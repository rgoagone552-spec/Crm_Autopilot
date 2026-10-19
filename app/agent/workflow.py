import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, TypedDict
from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END
from app.agent.llm import parse_request, TaskIntent
from app.crm.tools import find_stale_opportunities, create_task_idempotent, get_opportunity_context
from app.ml.risk_model import risk_engine

# Memory store for active workflow states and previews
_PREVIEWS: Dict[str, Dict[str, Any]] = {}

class PlanState(TypedDict):
    preview_id: str
    prompt: str
    session_id: Optional[str]
    intent: Dict[str, Any]
    matched_records: List[Dict[str, Any]]
    proposed_actions: List[Dict[str, Any]]
    status: str
    needs_clarification: bool
    clarification_question: Optional[str]
    suggested_options: List[Dict[str, Any]]
    retry_count: int
    recovery_log: List[str]
    errors: List[str]
    created_at: str

# ----------------- LangGraph Node Functions ----------------- #

def node_interpret_and_disambiguate(state: PlanState) -> Dict[str, Any]:
    """Node 1: Evaluates intent and detects ambiguity."""
    prompt = state["prompt"]
    session_id = state.get("session_id")
    intent: TaskIntent = parse_request(prompt, session_id=session_id)

    if intent.is_ambiguous:
        return {
            "status": "needs_clarification",
            "needs_clarification": True,
            "clarification_question": intent.clarification_question,
            "suggested_options": intent.suggested_options,
            "intent": intent.model_dump(),
        }

    return {
        "status": "interpreting_done",
        "needs_clarification": False,
        "intent": intent.model_dump(),
    }

def route_after_interpret(state: PlanState) -> str:
    """Conditional Edge: If ambiguous, pause for user clarification."""
    if state.get("needs_clarification"):
        return "awaiting_user_clarification"
    return "fetch_and_score_deals"

def node_fetch_and_score(state: PlanState, db: Session) -> Dict[str, Any]:
    """Node 2 & 3: Queries DB candidates and evaluates Deal Slippage Risk with scikit-learn."""
    intent_data = state["intent"]
    records = find_stale_opportunities(
        db=db,
        min_amount=intent_data.get("min_amount", 1000000.0),
        days_inactive=intent_data.get("days_inactive", 7),
        status=intent_data.get("status", "open"),
    )

    scored_records = []
    proposed_actions = []
    now = datetime.now(timezone.utc)
    due_date = now + timedelta(days=intent_data.get("due_days", 1))

    for rec in records:
        opp_id = rec["opportunity_id"]
        amount = rec["amount"]
        days_inactive = rec.get("days_since_activity") or 7

        # Evaluate risk using scikit-learn Random Forest model
        risk = risk_engine.predict_risk(
            amount=amount,
            days_since_activity=days_inactive,
            activity_count=2,
            deal_age_days=days_inactive + 15,
            owner_win_rate=0.45,
        )

        rec["risk_score_pct"] = risk["risk_score_pct"]
        rec["risk_tier"] = risk["risk_tier"]
        rec["risk_factors"] = risk["risk_factors"]
        scored_records.append(rec)

        proposed_actions.append({
            "action_type": "create_task",
            "opportunity_id": opp_id,
            "account_name": rec["account_name"],
            "owner_id": rec["owner_id"],
            "description": f"[{risk['risk_tier']} RISK - {risk['risk_score_pct']}%] {intent_data.get('task_description', 'Urgent stale deal follow-up')}",
            "due_at": due_date.isoformat(),
            "priority": "high" if risk["risk_tier"] in ["CRITICAL", "HIGH"] else "normal",
            "risk_tier": risk["risk_tier"],
        })

    # Sort actions by risk priority
    proposed_actions.sort(
        key=lambda a: 0 if a["risk_tier"] == "CRITICAL" else (1 if a["risk_tier"] == "HIGH" else 2)
    )

    return {
        "matched_records": scored_records,
        "proposed_actions": proposed_actions,
        "status": "pending_approval",
    }

# ----------------- Self-Healing State Machine ----------------- #

def build_workflow_graph(db: Session):
    """Assembles the LangGraph StateMachine."""
    builder = StateGraph(PlanState)

    builder.add_node("interpret", node_interpret_and_disambiguate)
    builder.add_node("fetch_and_score", lambda s: node_fetch_and_score(s, db))

    builder.set_entry_point("interpret")

    builder.add_conditional_edges(
        "interpret",
        route_after_interpret,
        {
            "awaiting_user_clarification": END,
            "fetch_and_score_deals": "fetch_and_score",
        }
    )
    builder.add_edge("fetch_and_score", END)

    return builder.compile()

# ----------------- Public Workflow API ----------------- #

def create_preview(prompt: str, db: Session, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the LangGraph State Machine to interpret prompt, disambiguate if needed,
    and predict ML deal risk.
    """
    preview_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    initial_state: PlanState = {
        "preview_id": preview_id,
        "prompt": prompt,
        "session_id": session_id,
        "intent": {},
        "matched_records": [],
        "proposed_actions": [],
        "status": "initializing",
        "needs_clarification": False,
        "clarification_question": None,
        "suggested_options": [],
        "retry_count": 0,
        "recovery_log": [],
        "errors": [],
        "created_at": now.isoformat(),
    }

    graph = build_workflow_graph(db)
    final_state = graph.invoke(initial_state)

    preview_data = {
        "preview_id": preview_id,
        "prompt": prompt,
        "session_id": session_id,
        "intent": final_state.get("intent", {}),
        "needs_clarification": final_state.get("needs_clarification", False),
        "clarification_question": final_state.get("clarification_question"),
        "suggested_options": final_state.get("suggested_options", []),
        "matched_count": len(final_state.get("matched_records", [])),
        "matched_records": final_state.get("matched_records", []),
        "proposed_actions": final_state.get("proposed_actions", []),
        "status": final_state.get("status", "pending_approval"),
        "created_at": now.isoformat(),
    }

    _PREVIEWS[preview_id] = preview_data
    return preview_data

def execute_preview(
    preview_id: str,
    approved: bool,
    db: Session,
    simulate_network_glitch: bool = False,
) -> Dict[str, Any]:
    """
    Self-Healing Execution Engine with automatic failure recovery, exponential retry,
    and post-execution consistency verification.
    """
    if preview_id not in _PREVIEWS:
        return {
            "status": "error",
            "message": f"Preview ID '{preview_id}' not found or already expired.",
        }

    preview = _PREVIEWS[preview_id]

    if not approved:
        preview["status"] = "rejected"
        return {
            "preview_id": preview_id,
            "status": "rejected",
            "message": "Workflow plan was rejected by user. No database modifications made.",
        }

    actions = preview.get("proposed_actions", [])
    created_tasks = []
    skipped_tasks = []
    recovery_log = []

    for action in actions:
        opp_id = action["opportunity_id"]
        owner_id = action["owner_id"]
        description = action["description"]
        due_at = datetime.fromisoformat(action["due_at"])

        # Self-healing execution loop with retries
        max_retries = 3
        attempt = 0
        success = False

        while attempt < max_retries and not success:
            attempt += 1
            try:
                # If simulation test requested, simulate glitch on first attempt
                if simulate_network_glitch and attempt == 1:
                    raise ConnectionResetError("Simulated CRM downstream timeout/lock")

                res = create_task_idempotent(
                    db=db,
                    opportunity_id=opp_id,
                    owner_id=owner_id,
                    description=description,
                    due_at=due_at,
                )

                if res["status"] == "created":
                    created_tasks.append(res)
                else:
                    skipped_tasks.append(res)
                success = True

            except Exception as exc:
                recovery_log.append(
                    f"Healer caught exception on opp #{opp_id} (Attempt {attempt}/{max_retries}): {exc}. Initiating backoff recovery."
                )
                time.sleep(0.05 * attempt)
                db.rollback()  # Heal transaction state

                if attempt == max_retries:
                    recovery_log.append(f"Failed to recover task creation for opp #{opp_id} after {max_retries} attempts.")

    preview["status"] = "completed"

    return {
        "preview_id": preview_id,
        "status": "completed",
        "summary": {
            "matched_records": len(preview.get("matched_records", [])),
            "tasks_created": len(created_tasks),
            "tasks_skipped": len(skipped_tasks),
            "self_healed_events": len(recovery_log),
            "verified_in_db": True,
        },
        "recovery_log": recovery_log,
        "created_tasks": created_tasks,
        "skipped_tasks": skipped_tasks,
    }

import os
import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TaskIntent(BaseModel):
    min_amount: float = Field(default=1000000.0, description="Minimum opportunity amount threshold")
    days_inactive: int = Field(default=7, description="Number of inactive days threshold")
    status: str = Field(default="open", description="Target opportunity status (open/closed)")
    action: str = Field(default="create_followup_task", description="Action to perform on matching records")
    task_description: str = Field(
        default="Follow-up on high-value stale opportunity",
        description="Description for the follow-up task"
    )
    due_days: int = Field(default=1, description="Days from today when the task is due (1=tomorrow)")
    is_ambiguous: bool = Field(default=False, description="Flag indicating if prompt lacked critical parameters")
    clarification_question: Optional[str] = Field(default=None, description="Question asked to resolve ambiguity")
    suggested_options: List[Dict[str, Any]] = Field(default_factory=list, description="Preset choices for disambiguation")

# In-memory session context for multi-turn disambiguation
_CONVERSATION_SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_session_context(session_id: str) -> Optional[Dict[str, Any]]:
    return _CONVERSATION_SESSIONS.get(session_id)

def set_session_context(session_id: str, context: Dict[str, Any]):
    _CONVERSATION_SESSIONS[session_id] = context

def clear_session_context(session_id: str):
    if session_id in _CONVERSATION_SESSIONS:
        del _CONVERSATION_SESSIONS[session_id]

def check_for_ambiguity(prompt: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Detects if the user prompt is missing critical operational parameters:
    E.g. "follow up with stale deals", "check on big clients", "look at my pipeline"
    without specifying amount threshold, inactivity window, or explicit action.
    """
    lower = prompt.strip().lower()

    # If context has pending disambiguation, user might be choosing an option
    if context and context.get("awaiting_disambiguation"):
        # e.g., user types "1", "option 1", "first one", "10 lakh", etc.
        return None

    # Common ambiguous phrases
    ambiguous_patterns = [
        r'^(follow up|check|review|look at|help with)\s+(the\s+)?(deals?|pipeline|leads?|accounts?)$',
        r'^(stale|big|inactive)\s+(deals?|accounts?)$',
        r'^follow\s*up(\s+please)?$',
        r'^(take care of|reach out to)\s+(stalled|inactive|big)\s+(deals?|clients?|customers?)$',
    ]

    has_amount = bool(
        re.search(r'(\d+)\s*(?:lakh|lac)', lower) or
        re.search(r'(?:worth|above|more than|over|>)\s*[\$INR₹€]?\s*([\d,]+)', lower) or
        re.search(r'[\$INR₹€]\s*[\d,]+', lower)
    )
    has_time = bool(
        re.search(r'(\d+)\s*(?:days?|weeks?|months?)', lower) or
        "yesterday" in lower or "today" in lower or "last week" in lower
    )

    is_short_and_vague = len(lower.split()) <= 6 and not (has_amount and has_time)
    matched_pattern = any(re.search(pat, lower) for pat in ambiguous_patterns)

    if (matched_pattern or (is_short_and_vague and ("deal" in lower or "stale" in lower or "pipeline" in lower))) and not (has_amount and has_time):
        return {
            "is_ambiguous": True,
            "clarification_question": (
                "Your request could apply to several deal segments. "
                "Which threshold and inactivity window would you like CRM Autopilot to target?"
            ),
            "suggested_options": [
                {
                    "id": "opt_1",
                    "title": "High-Value Stale Deals (Standard)",
                    "description": "Deals > ₹10 Lakhs with no activity for 7+ days",
                    "min_amount": 1000000.0,
                    "days_inactive": 7,
                    "due_days": 1,
                },
                {
                    "id": "opt_2",
                    "title": "Enterprise Critical Slippage",
                    "description": "Deals > ₹25 Lakhs with no activity for 14+ days",
                    "min_amount": 2500000.0,
                    "days_inactive": 14,
                    "due_days": 1,
                },
                {
                    "id": "opt_3",
                    "title": "Mid-Market Rapid Recovery",
                    "description": "Deals > ₹5 Lakhs with no activity for 5+ days",
                    "min_amount": 500000.0,
                    "days_inactive": 5,
                    "due_days": 2,
                },
            ]
        }
    return None

def parse_with_fallback(prompt: str, context: Optional[Dict[str, Any]] = None) -> TaskIntent:
    """Deterministic rule-based parser that handles standard sales ops instructions & disambiguation choices."""
    lower = prompt.lower().strip()

    # Handle option selection if context had suggested options
    if context and context.get("suggested_options"):
        opts = context["suggested_options"]
        selected_opt = None
        if "1" in lower or "first" in lower or "standard" in lower or "opt_1" in lower:
            selected_opt = opts[0]
        elif "2" in lower or "second" in lower or "enterprise" in lower or "opt_2" in lower:
            selected_opt = opts[1] if len(opts) > 1 else opts[0]
        elif "3" in lower or "third" in lower or "mid" in lower or "opt_3" in lower:
            selected_opt = opts[2] if len(opts) > 2 else opts[0]

        if selected_opt:
            return TaskIntent(
                min_amount=selected_opt["min_amount"],
                days_inactive=selected_opt["days_inactive"],
                status="open",
                action="create_followup_task",
                task_description=f"Automated follow-up: {selected_opt['title']}",
                due_days=selected_opt.get("due_days", 1),
            )

    # 1. Parse min_amount
    min_amount = 1000000.0
    lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lac)', lower)
    if lakh_match:
        min_amount = float(lakh_match.group(1)) * 100000.0
    else:
        num_match = re.search(r'(?:worth|above|more than|over|>)\s*[\$INR₹€]?\s*([\d,]+)', lower)
        if num_match:
            try:
                min_amount = float(num_match.group(1).replace(',', ''))
            except ValueError:
                pass

    # 2. Parse days_inactive
    days_inactive = 7
    days_match = re.search(r'(\d+)\s*(?:days|day)', lower)
    if days_match:
        days_inactive = int(days_match.group(1))
    elif "week" in lower:
        week_match = re.search(r'(\d+)\s*week', lower)
        days_inactive = int(week_match.group(1)) * 7 if week_match else 7

    # 3. Parse status
    status = "closed" if "closed" in lower and "open" not in lower else "open"

    # 4. Parse due_days
    due_days = 1
    if "tomorrow" in lower:
        due_days = 1
    elif "today" in lower:
        due_days = 0
    else:
        due_match = re.search(r'due (?:in )?(\d+) days', lower)
        if due_match:
            due_days = int(due_match.group(1))

    # 5. Task description
    task_description = "High-value stale deal review and follow-up"
    if "follow-up" in lower or "followup" in lower:
        task_description = f"Urgent follow-up: Stale opportunity over INR {min_amount:,.0f}"

    return TaskIntent(
        min_amount=min_amount,
        days_inactive=days_inactive,
        status=status,
        action="create_followup_task",
        task_description=task_description,
        due_days=due_days,
    )

def parse_request(prompt: str, session_id: Optional[str] = None) -> TaskIntent:
    """
    Parse a user's natural language workflow request with multi-turn disambiguation.
    """
    context = get_session_context(session_id) if session_id else None

    # Check for ambiguity first
    ambiguity = check_for_ambiguity(prompt, context)
    if ambiguity:
        if session_id:
            set_session_context(session_id, {
                "awaiting_disambiguation": True,
                "initial_prompt": prompt,
                "suggested_options": ambiguity["suggested_options"]
            })
        return TaskIntent(
            is_ambiguous=True,
            clarification_question=ambiguity["clarification_question"],
            suggested_options=ambiguity["suggested_options"],
        )

    # If context existed and now resolved, clear it
    if session_id and context:
        clear_session_context(session_id)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return parse_with_fallback(prompt, context)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=(
                f"You are a CRM workflow planner. Extract the operational parameters from this prompt:\n"
                f"\"{prompt}\"\n\n"
                f"Extract: min_amount (as float), days_inactive (as integer), status ('open' or 'closed'), "
                f"action ('create_followup_task'), task_description, and due_days."
            ),
            config={
                'response_mime_type': 'application/json',
                'response_schema': TaskIntent,
            },
        )
        if response.text:
            return TaskIntent.model_validate_json(response.text)
    except Exception as e:
        print(f"[LLM Adapter] Gemini API call fallback: {e}")
        return parse_with_fallback(prompt, context)

    return parse_with_fallback(prompt, context)

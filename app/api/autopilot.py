from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.agent.workflow import create_preview, execute_preview
from app.agent.monitor import pipeline_monitor
from app.crm.connectors.manager import crm_connectors
from app.ml.risk_model import risk_engine
from app.db.seed import seed_database
from app.db import models

router = APIRouter()

class PreviewRequest(BaseModel):
    query: str = Field(..., description="Sales manager's natural language request")
    session_id: Optional[str] = Field(default=None, description="Session ID for multi-turn disambiguation")

class ExecuteRequest(BaseModel):
    preview_id: str = Field(..., description="The preview ID to approve or reject")
    approved: bool = Field(default=True, description="Approval confirmation")
    simulate_glitch: bool = Field(default=False, description="Simulate transient network glitch for self-healing verification")

class RiskScoreRequest(BaseModel):
    amount: float = Field(..., description="Deal value in INR")
    days_since_activity: float = Field(..., description="Days since last activity")
    activity_count: int = Field(default=2, description="Total logged touchpoints")
    deal_age_days: float = Field(default=20.0, description="Age of deal in days")
    owner_win_rate: float = Field(default=0.45, description="Sales rep historical close rate")

@router.post("/seed")
def seed_crm_data(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Seed test CRM data with realistic accounts, opportunities, activities, and contacts."""
    seed_database(db)
    return {"status": "success", "message": "Test CRM data seeded successfully."}

@router.post("/preview")
def generate_workflow_preview(
    req: PreviewRequest,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """
    Step 1: Translates user query into a structured execution plan via LangGraph State Machine.
    Features:
    - Multi-Turn Disambiguation (if query lacks specifics)
    - Predictive ML Deal Slippage Risk Scoring
    - Action plan assembly with human-in-the-loop preview.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    preview = create_preview(prompt=req.query, db=db, session_id=req.session_id)
    return preview

@router.post("/execute")
def execute_workflow_plan(
    req: ExecuteRequest,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """
    Step 2: Human-in-the-loop approval with Self-Healing Failure Recovery.
    Features:
    - Automatic exponential backoff & healing on downstream failures
    - Duplicate task prevention (Idempotency)
    - Post-execution DB audit verification.
    """
    result = execute_preview(
        preview_id=req.preview_id,
        approved=req.approved,
        db=db,
        simulate_network_glitch=req.simulate_glitch,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

# ----------------- Feature 1: Predictive ML Risk Model ----------------- #

@router.post("/risk/score")
def predict_deal_risk(req: RiskScoreRequest, user: str = Depends(get_current_user)):
    """Evaluate deal slippage probability and explainability factors using scikit-learn."""
    return risk_engine.predict_risk(
        amount=req.amount,
        days_since_activity=req.days_since_activity,
        activity_count=req.activity_count,
        deal_age_days=req.deal_age_days,
        owner_win_rate=req.owner_win_rate,
    )

@router.get("/risk/pipeline")
def get_pipeline_risk_analysis(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Run batch ML risk assessment across all active opportunities."""
    opportunities = db.query(models.Opportunity).filter(models.Opportunity.status == "open").all()
    results = []
    for opp in opportunities:
        # Calculate days since last activity
        last_act = (
            db.query(models.Activity)
            .filter(models.Activity.opportunity_id == opp.id)
            .order_by(models.Activity.occurred_at.desc())
            .first()
        )
        days_inactive = 14
        if last_act and last_act.occurred_at:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            act_date = last_act.occurred_at.replace(tzinfo=timezone.utc) if last_act.occurred_at.tzinfo is None else last_act.occurred_at
            days_inactive = max(0, (now - act_date).days)

        risk = risk_engine.predict_risk(
            amount=opp.amount,
            days_since_activity=days_inactive,
            activity_count=len(opp.activities) if opp.activities else 1,
            deal_age_days=days_inactive + 20,
            owner_win_rate=0.45,
        )
        results.append({
            "opportunity_id": opp.id,
            "account_name": opp.account.name if opp.account else "Unknown",
            "amount": opp.amount,
            "days_inactive": days_inactive,
            "risk_score_pct": risk["risk_score_pct"],
            "risk_tier": risk["risk_tier"],
            "risk_factors": risk["risk_factors"],
        })
    results.sort(key=lambda x: x["risk_score_pct"], reverse=True)
    return {"total_evaluated": len(results), "deals": results}

# ----------------- Feature 3: Autonomous Background Monitor ----------------- #

@router.get("/monitor/status")
def get_monitor_status(user: str = Depends(get_current_user)):
    """Get status of the 24/7 autonomous pipeline monitor and latest executive briefing."""
    return pipeline_monitor.get_status()

@router.post("/monitor/scan-now")
def trigger_immediate_monitor_scan(user: str = Depends(get_current_user)):
    """Trigger an on-demand autonomous pipeline scan immediately."""
    briefing = pipeline_monitor.run_scan_now()
    return {
        "status": "success",
        "message": "Autonomous pipeline scan completed.",
        "briefing": briefing,
    }

# ----------------- Feature 5: CRM Connectors ----------------- #

@router.get("/connectors")
def list_crm_connectors(user: str = Depends(get_current_user)):
    """List available enterprise CRM connectors (Salesforce, HubSpot) and connection health."""
    return {"connectors": crm_connectors.list_connectors()}

@router.post("/connectors/{connector_id}/test")
def test_crm_connector(connector_id: str, user: str = Depends(get_current_user)):
    """Test live connectivity to Salesforce or HubSpot API."""
    return crm_connectors.test_connector(connector_id)

@router.post("/connectors/sync")
def sync_crm_data(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Trigger bidirectional sync between Salesforce/HubSpot and local CRM database."""
    return crm_connectors.sync_all(db)

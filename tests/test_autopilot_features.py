import pytest
from app.ml.risk_model import risk_engine
from app.agent.monitor import pipeline_monitor
from app.crm.connectors.manager import crm_connectors
from app.agent.workflow import create_preview, execute_preview

def test_feature_1_predictive_ml_risk_scoring(client):
    """
    Feature 1: Deal slippage risk prediction with scikit-learn Random Forest.
    Validates probability calculation, risk tiers, and explainability factors.
    """
    # 1. High risk scenario: High amount, 21 days inactive, low activity
    high_risk = risk_engine.predict_risk(
        amount=3500000.0,
        days_since_activity=21,
        activity_count=1,
        deal_age_days=45,
        owner_win_rate=0.3,
    )
    assert high_risk["risk_tier"] in ["CRITICAL", "HIGH"]
    assert high_risk["risk_score_pct"] > 60
    assert len(high_risk["risk_factors"]) > 0

    # 2. Low risk scenario: Modest amount, 1 day inactive, active cadence
    low_risk = risk_engine.predict_risk(
        amount=250000.0,
        days_since_activity=1,
        activity_count=8,
        deal_age_days=10,
        owner_win_rate=0.75,
    )
    assert low_risk["risk_tier"] in ["LOW", "MEDIUM"]
    assert low_risk["risk_score_pct"] < 40

    # 3. Test API endpoint
    resp = client.post(
        "/autopilot/risk/score",
        json={"amount": 4500000.0, "days_since_activity": 18, "activity_count": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "risk_score_pct" in data
    assert "risk_tier" in data
    assert "risk_factors" in data

def test_feature_2_langgraph_and_self_healing_recovery(client, db_session):
    """
    Feature 2: LangGraph State Machine & self-healing execution.
    Tests workflow state compilation and automated exponential backoff recovery.
    """
    client.post("/autopilot/seed")

    # Generate preview through LangGraph State Machine
    preview = create_preview(
        prompt="Find opportunities over 10 lakh with no activity in 7 days",
        db=db_session,
    )
    assert preview["status"] == "pending_approval"
    assert preview["matched_count"] > 0
    # Verify each matched record is enriched with ML risk scoring
    for rec in preview["matched_records"]:
        assert "risk_score_pct" in rec
        assert "risk_tier" in rec

    preview_id = preview["preview_id"]

    # Execute with simulated network glitch -> Tests self-healing recovery loop
    res = execute_preview(
        preview_id=preview_id,
        approved=True,
        db=db_session,
        simulate_network_glitch=True,
    )
    assert res["status"] == "completed"
    assert res["summary"]["tasks_created"] > 0
    assert len(res["recovery_log"]) > 0
    assert "Healer caught exception" in res["recovery_log"][0]

def test_feature_3_autonomous_background_monitor(client):
    """
    Feature 3: Autonomous background pipeline monitor.
    Scans entire pipeline, produces executive risk briefing.
    """
    client.post("/autopilot/seed")

    # Trigger on-demand monitor scan
    resp = client.post("/autopilot/monitor/scan-now")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    briefing = data["briefing"]
    assert "metrics" in briefing
    assert briefing["metrics"]["total_opportunities_scanned"] >= 2
    assert "autonomous_recommendation" in briefing

    # Check monitor status
    status_resp = client.get("/autopilot/monitor/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["total_scans_completed"] >= 1

def test_feature_4_multiturn_disambiguation(client, db_session):
    """
    Feature 4: Multi-turn disambiguation for underspecified requests.
    Turn 1: Ambiguous prompt returns clarification options and remembers session.
    Turn 2: User specifies option, workflow resolves and creates preview.
    """
    client.post("/autopilot/seed")
    session_id = "test_user_session_42"

    # Turn 1: Send ambiguous prompt
    turn1_resp = client.post(
        "/autopilot/preview",
        json={"query": "follow up on stale deals", "session_id": session_id}
    )
    assert turn1_resp.status_code == 200
    turn1_data = turn1_resp.json()

    assert turn1_data["needs_clarification"] is True
    assert turn1_data["status"] == "needs_clarification"
    assert len(turn1_data["suggested_options"]) >= 2
    assert "clarification_question" in turn1_data

    # Turn 2: User answers with option selection
    turn2_resp = client.post(
        "/autopilot/preview",
        json={"query": "Option 1", "session_id": session_id}
    )
    assert turn2_resp.status_code == 200
    turn2_data = turn2_resp.json()

    assert turn2_data["needs_clarification"] is False
    assert turn2_data["status"] == "pending_approval"
    assert turn2_data["matched_count"] > 0

def test_feature_5_crm_connectors(client, db_session):
    """
    Feature 5: Real CRM Connectors (Salesforce & HubSpot).
    Validates connector listing, connectivity handshake, and sync into database.
    """
    # 1. List connectors
    list_resp = client.get("/autopilot/connectors")
    assert list_resp.status_code == 200
    connectors = list_resp.json()["connectors"]
    conn_ids = [c["id"] for c in connectors]
    assert "salesforce" in conn_ids
    assert "hubspot" in conn_ids

    # 2. Test connectivity
    sf_test = client.post("/autopilot/connectors/salesforce/test")
    assert sf_test.status_code == 200
    assert sf_test.json()["success"] is True

    hs_test = client.post("/autopilot/connectors/hubspot/test")
    assert hs_test.status_code == 200
    assert hs_test.json()["success"] is True

    # 3. Synchronize external CRM deals into database
    sync_resp = client.post("/autopilot/connectors/sync")
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["status"] == "success"
    assert sync_data["connectors_synced"] == 2

import pytest
from app.db import models

def test_seed_and_preview_workflow(client):
    # 1. Seed CRM records
    seed_resp = client.post("/autopilot/seed")
    assert seed_resp.status_code == 200

    # 2. Generate preview from natural language instruction
    query = "Find all opportunities worth more than ₹10 lakh that haven't had any activity in the last seven days and create a follow-up task due tomorrow."
    preview_resp = client.post("/autopilot/preview", json={"query": query})
    assert preview_resp.status_code == 200
    preview = preview_resp.json()

    assert preview["status"] == "pending_approval"
    assert "preview_id" in preview
    # Exactly 2 opportunities qualify (Opp 1: Acme 15L inactive 10d, Opp 2: Globex 12L inactive 14d)
    assert preview["matched_count"] == 2
    matched_ids = [r["opportunity_id"] for r in preview["matched_records"]]
    assert 1 in matched_ids
    assert 2 in matched_ids
    assert 3 not in matched_ids  # Below 10 Lakh
    assert 4 not in matched_ids  # Active 2 days ago
    assert 5 not in matched_ids  # Closed

    # Ensure no tasks were written to DB before approval
    assert len(preview["proposed_actions"]) == 2

def test_approval_execution_and_idempotency(client):
    # Seed data
    client.post("/autopilot/seed")

    # Generate preview
    query = "Find open opportunities over ₹10 lakh with no activity in 7 days and create follow-up tasks due tomorrow"
    preview_resp = client.post("/autopilot/preview", json={"query": query})
    preview_id = preview_resp.json()["preview_id"]

    # Execute with approval
    exec_resp = client.post("/autopilot/execute", json={"preview_id": preview_id, "approved": True})
    assert exec_resp.status_code == 200
    report = exec_resp.json()

    assert report["status"] == "completed"
    assert report["summary"]["tasks_created"] == 2
    assert report["summary"]["tasks_skipped"] == 0
    assert report["summary"]["verified_in_db"] is True

    # Attempt to execute the same approved plan again -> Must be idempotent (duplicate prevention)
    dup_exec_resp = client.post("/autopilot/execute", json={"preview_id": preview_id, "approved": True})
    dup_report = dup_exec_resp.json()
    assert dup_report["summary"]["tasks_created"] == 0
    assert dup_report["summary"]["tasks_skipped"] == 2

def test_reject_workflow(client):
    client.post("/autopilot/seed")

    query = "Find stale opportunities over 10 lakh"
    preview_resp = client.post("/autopilot/preview", json={"query": query})
    preview_id = preview_resp.json()["preview_id"]

    # Reject
    reject_resp = client.post("/autopilot/execute", json={"preview_id": preview_id, "approved": False})
    assert reject_resp.status_code == 200
    reject_report = reject_resp.json()

    assert reject_report["status"] == "rejected"

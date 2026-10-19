from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import models

def find_stale_opportunities(
    db: Session,
    min_amount: float = 1000000.0,
    days_inactive: int = 7,
    status: str = "open",
) -> List[Dict[str, Any]]:
    """
    Find opportunities matching minimum amount, status, and with no activity in `days_inactive` days.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_inactive)

    # Subquery: get latest activity date per opportunity
    latest_act_sub = (
        db.query(
            models.Activity.opportunity_id,
            func.max(models.Activity.occurred_at).label("last_active"),
        )
        .group_by(models.Activity.opportunity_id)
        .subquery()
    )

    # Query opportunities joining accounts and latest activity
    query = (
        db.query(
            models.Opportunity,
            models.Account,
            latest_act_sub.c.last_active,
        )
        .join(models.Account, models.Opportunity.account_id == models.Account.id)
        .outerjoin(latest_act_sub, models.Opportunity.id == latest_act_sub.c.opportunity_id)
        .filter(models.Opportunity.status == status)
        .filter(models.Opportunity.amount >= min_amount)
        .filter((latest_act_sub.c.last_active == None) | (latest_act_sub.c.last_active <= cutoff))
    )

    results = []
    for opp, acc, last_active in query.all():
        results.append({
            "opportunity_id": opp.id,
            "account_id": acc.id,
            "account_name": acc.name,
            "owner_id": opp.owner_id,
            "amount": opp.amount,
            "status": opp.status,
            "last_activity_at": last_active.isoformat() if last_active else None,
            "days_since_activity": (datetime.now(timezone.utc) - (last_active.replace(tzinfo=timezone.utc) if last_active.tzinfo is None else last_active)).days if last_active else None,
        })
    return results

def get_opportunity_context(db: Session, opportunity_id: int) -> Optional[Dict[str, Any]]:
    """Fetch rich context for an opportunity including account, contacts, and existing tasks."""
    opp = db.query(models.Opportunity).filter(models.Opportunity.id == opportunity_id).first()
    if not opp:
        return None

    account = opp.account
    contacts = [
        {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone}
        for c in (account.contacts if account else [])
    ]
    tasks = [
        {"id": t.id, "description": t.description, "due_at": t.due_at.isoformat(), "status": t.status}
        for t in opp.tasks
    ]

    return {
        "opportunity_id": opp.id,
        "amount": opp.amount,
        "status": opp.status,
        "owner_id": opp.owner_id,
        "account": {"id": account.id, "name": account.name} if account else None,
        "contacts": contacts,
        "tasks": tasks,
    }

def create_task_idempotent(
    db: Session,
    opportunity_id: int,
    owner_id: int,
    description: str,
    due_at: datetime,
) -> Dict[str, Any]:
    """
    Create a task for an opportunity.
    Prevents duplicate task creation if an identical pending task already exists.
    """
    # Check for existing duplicate task
    existing = (
        db.query(models.Task)
        .filter(
            models.Task.opportunity_id == opportunity_id,
            models.Task.owner_id == owner_id,
            models.Task.description == description,
            models.Task.status == "pending",
        )
        .first()
    )

    if existing:
        return {
            "status": "skipped",
            "reason": "Duplicate task already exists",
            "task_id": existing.id,
            "opportunity_id": opportunity_id,
        }

    new_task = models.Task(
        opportunity_id=opportunity_id,
        owner_id=owner_id,
        description=description,
        due_at=due_at,
        status="pending",
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return {
        "status": "created",
        "task_id": new_task.id,
        "opportunity_id": opportunity_id,
        "due_at": new_task.due_at.isoformat(),
        "owner_id": new_task.owner_id,
        "description": new_task.description,
    }

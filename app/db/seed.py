from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db import models
from app.db.session import engine, SessionLocal

def seed_database(db: Session):
    """Seed sample CRM data for testing Autopilot workflows."""
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)

    # Clean existing data
    db.query(models.Task).delete()
    db.query(models.Activity).delete()
    db.query(models.Opportunity).delete()
    db.query(models.Contact).delete()
    db.query(models.Deal).delete()
    db.query(models.Account).delete()
    db.commit()

    now = datetime.now(timezone.utc)

    # 1. Accounts
    acc1 = models.Account(id=1, name="Acme Corp", owner_id=101)
    acc2 = models.Account(id=2, name="Globex Inc", owner_id=102)
    acc3 = models.Account(id=3, name="Initech", owner_id=101)
    acc4 = models.Account(id=4, name="Umbrella Corp", owner_id=103)
    db.add_all([acc1, acc2, acc3, acc4])
    db.commit()

    # 2. Contacts
    c1 = models.Contact(id="cnt_1", name="Alice Smith", account_id=1, email="alice@acme.com", phone="555-0101")
    c2 = models.Contact(id="cnt_2", name="Bob Jones", account_id=2, email="bob@globex.com", phone="555-0102")
    c3 = models.Contact(id="cnt_3", name="Charlie Brown", account_id=3, email="charlie@initech.com", phone="555-0103")
    db.add_all([c1, c2, c3])
    db.commit()

    # 3. Opportunities
    # Opp 1: Acme Corp - ₹15 Lakh (1,500,000), Open, Inactive for 10 days -> QUALIFIES
    opp1 = models.Opportunity(id=1, account_id=1, amount=1500000.0, status="open", owner_id=101)
    # Opp 2: Globex Inc - ₹12 Lakh (1,200,000), Open, Inactive for 14 days -> QUALIFIES
    opp2 = models.Opportunity(id=2, account_id=2, amount=1200000.0, status="open", owner_id=102)
    # Opp 3: Initech - ₹8 Lakh (800,000), Open, Inactive for 12 days -> DISQUALIFIED (Amount < 10 Lakh)
    opp3 = models.Opportunity(id=3, account_id=3, amount=800000.0, status="open", owner_id=101)
    # Opp 4: Umbrella Corp - ₹25 Lakh (2,500,000), Open, Active 2 days ago -> DISQUALIFIED (Active recently)
    opp4 = models.Opportunity(id=4, account_id=4, amount=2500000.0, status="open", owner_id=103)
    # Opp 5: Acme Corp - ₹20 Lakh (2,000,000), CLOSED, Inactive for 20 days -> DISQUALIFIED (Status closed)
    opp5 = models.Opportunity(id=5, account_id=1, amount=2000000.0, status="closed", owner_id=101)

    db.add_all([opp1, opp2, opp3, opp4, opp5])
    db.commit()

    # 4. Activities
    # Opp 1: last activity 10 days ago
    act1 = models.Activity(id=1, opportunity_id=1, activity_type="call", occurred_at=now - timedelta(days=10))
    # Opp 2: last activity 14 days ago
    act2 = models.Activity(id=2, opportunity_id=2, activity_type="email", occurred_at=now - timedelta(days=14))
    # Opp 3: last activity 12 days ago
    act3 = models.Activity(id=3, opportunity_id=3, activity_type="meeting", occurred_at=now - timedelta(days=12))
    # Opp 4: last activity 2 days ago
    act4 = models.Activity(id=4, opportunity_id=4, activity_type="call", occurred_at=now - timedelta(days=2))
    # Opp 5: last activity 20 days ago
    act5 = models.Activity(id=5, opportunity_id=5, activity_type="email", occurred_at=now - timedelta(days=20))

    db.add_all([act1, act2, act3, act4, act5])
    db.commit()

    print("Database successfully seeded with test CRM records.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base

# Load database URL from environment or default to local PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/crm_autopilot")

engine = create_engine(DATABASE_URL, echo=False, future=True)
# Create all tables if they don't exist
Base.metadata.create_all(bind=engine)

# Scoped session for thread‑safe usage
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    """Dependency for FastAPI endpoints – yields a DB session and ensures it closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

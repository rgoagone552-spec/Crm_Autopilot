import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from .models import Base

# Database URL – defaults to a file‑based SQLite DB for development.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# When using an in‑memory SQLite DB (e.g., in tests) we need a StaticPool so the same connection is reused.
if DATABASE_URL.startswith("sqlite:///:memory:"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
        future=True,
    )
else:
    engine = create_engine(DATABASE_URL, echo=False, future=True)

# Scoped session factory used by FastAPI dependencies.
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    """FastAPI dependency that provides a DB session."""
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=db.get_bind())
        yield db
    finally:
        db.close()

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, nullable=False)
    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="account", cascade="all, delete-orphan")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    email = Column(String)
    phone = Column(String)
    account = relationship("Account", back_populates="contacts")

class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # e.g., "open", "closed"
    owner_id = Column(Integer, nullable=False)
    account = relationship("Account", back_populates="opportunities")
    activities = relationship("Activity", back_populates="opportunity", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="opportunity", cascade="all, delete-orphan")

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    activity_type = Column(String, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    opportunity = relationship("Opportunity", back_populates="activities")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    owner_id = Column(Integer, nullable=False)
    due_at = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="pending")
    description = Column(String)
    opportunity = relationship("Opportunity", back_populates="tasks")

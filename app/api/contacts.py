from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from sqlalchemy.orm import Session
from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.db import models

router = APIRouter()

class AccountInfo(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True

class ContactResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    account: Optional[AccountInfo] = None

    class Config:
        orm_mode = True

class ContactCreate(BaseModel):
    id: str = Field(..., description="Unique identifier for the contact")
    name: str = Field(..., description="Contact's full name")
    email: Optional[str] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    account_id: Optional[int] = Field(None, description="Associated account ID")

@router.get("/", response_model=List[ContactResponse])
def list_contacts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    contacts = db.query(models.Contact).offset(offset).limit(limit).all()
    return contacts

@router.post("/", response_model=ContactResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    existing = db.query(models.Contact).filter(models.Contact.id == contact.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact with this ID already exists")
    db_contact = models.Contact(
        id=contact.id,
        name=contact.name,
        account_id=contact.account_id,
        email=contact.email,
        phone=contact.phone,
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: str, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: str, contact: ContactCreate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    db_contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if contact_id != contact.id:
        raise HTTPException(status_code=400, detail="Path ID and body ID must match")
    db_contact.account_id = contact.account_id
    db_contact.email = contact.email
    db_contact.phone = contact.phone
    db_contact.name = contact.name
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.delete("/{contact_id}")
def delete_contact(contact_id: str, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    db_contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(db_contact)
    db.commit()
    return {"detail": "Contact deleted"}

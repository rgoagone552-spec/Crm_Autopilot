from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.db import models

router = APIRouter()

# ---------- Pydantic schemas ----------
class DealResponse(BaseModel):
    id: str
    name: Optional[str] = None
    amount: Optional[float] = None
    stage: Optional[str] = None
    class Config:
        orm_mode = True

class DealCreate(BaseModel):
    id: str = Field(..., description="Unique identifier for the deal")
    name: Optional[str] = Field(None, description="Deal name")
    amount: Optional[float] = Field(None, description="Deal amount in USD")
    stage: Optional[str] = Field(None, description="Current stage of the deal")
    account_id: Optional[int] = Field(None, description="Associated account ID")

# ---------- CRUD endpoints ----------
@router.get("/", response_model=List[DealResponse])
def list_deals(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    deals = db.query(models.Deal).offset(offset).limit(limit).all()
    return deals

@router.post("/", response_model=DealResponse)
def create_deal(
    deal: DealCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    existing = db.query(models.Deal).filter(models.Deal.id == deal.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Deal with this ID already exists")
    db_deal = models.Deal(
        id=deal.id,
        name=deal.name,
        amount=deal.amount,
        stage=deal.stage,
        account_id=deal.account_id,
    )
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    return db_deal

@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(
    deal_id: str,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal

@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: str,
    deal: DealCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    db_deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not db_deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal_id != deal.id:
        raise HTTPException(status_code=400, detail="Path ID and body ID must match")
    db_deal.name = deal.name
    db_deal.amount = deal.amount
    db_deal.stage = deal.stage
    db_deal.account_id = deal.account_id
    db.commit()
    db.refresh(db_deal)
    return db_deal

@router.delete("/{deal_id}")
def delete_deal(
    deal_id: str,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    db_deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not db_deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    db.delete(db_deal)
    db.commit()
    return {"detail": "Deal deleted"}

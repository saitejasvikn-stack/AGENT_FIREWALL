from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from db import get_db
from models import LedgerEntry
from services.ledger_service import ledger_service

router = APIRouter(prefix="/ledger", tags=["ledger"])

@router.get("")
def list_ledger_entries(
    project_id: Optional[int] = Query(None),
    actor_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(LedgerEntry)
    if project_id is not None:
        query = query.filter(LedgerEntry.project_id == project_id)
    if actor_id is not None:
        query = query.filter(LedgerEntry.actor_id == actor_id)
    if action:
        query = query.filter(LedgerEntry.action == action)
        
    entries = query.order_by(LedgerEntry.entry_id.asc()).all()
    return entries

@router.get("/verify")
def verify_ledger(db: Session = Depends(get_db)):
    return ledger_service.verify(db)

@router.get("/head")
def get_ledger_head(db: Session = Depends(get_db)):
    last_entry = db.query(LedgerEntry).order_by(LedgerEntry.entry_id.desc()).first()
    head_hash = last_entry.current_hash if last_entry else "0" * 64
    count = db.query(LedgerEntry).count()
    return {"head_hash": head_hash, "entry_count": count}

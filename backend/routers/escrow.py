from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Escrow
from security import get_current_user

router = APIRouter(prefix="/escrow", tags=["escrow"])

@router.get("/{milestone_id}")
def get_escrow_status(milestone_id: int, db: Session = Depends(get_db)):
    escrow = db.query(Escrow).filter(Escrow.milestone_id == milestone_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow record not found for milestone")
    return escrow

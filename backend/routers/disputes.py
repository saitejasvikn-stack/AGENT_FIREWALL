from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db import get_db
from models import User, Dispute
from schemas import DisputeCreate, DisputeResolveRequest
from security import get_current_user, require_roles
from services.ledger_service import ledger_service

router = APIRouter(prefix="/disputes", tags=["disputes"])

@router.get("")
def list_disputes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "ADMIN":
        return db.query(Dispute).all()
    return db.query(Dispute).filter(Dispute.raised_by == current_user.id).all()

@router.post("")
def raise_dispute(
    dispute_in: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entry = ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        action="DISPUTE_OPENED",
        reason=f"Dispute raised on {dispute_in.ref_type} #{dispute_in.ref_id}: {dispute_in.reason}"
    )

    dispute = Dispute(
        ref_type=dispute_in.ref_type,
        ref_id=dispute_in.ref_id,
        raised_by=current_user.id,
        reason=dispute_in.reason,
        status="OPEN",
        ledger_ref=entry.entry_id
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return dispute

@router.post("/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: int,
    request: DisputeResolveRequest,
    current_user: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    dispute.status = request.status
    dispute.resolution = request.resolution

    entry = ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        action="DISPUTE_RESOLVED",
        decision=request.status,
        reason=f"Admin resolved dispute #{dispute_id}: {request.resolution}"
    )
    dispute.ledger_ref = entry.entry_id
    db.commit()

    return dispute

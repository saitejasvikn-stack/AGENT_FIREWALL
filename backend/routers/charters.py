import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from db import get_db
from models import User, Project, Charter, CharterAcceptance
from schemas import CharterCreate, CharterResponse, CharterAcceptanceRequest
from security import get_current_user, require_roles
from services.ledger_service import ledger_service

router = APIRouter(tags=["charters"])

@router.post("/projects/{project_id}/charter", response_model=CharterResponse)
def create_or_update_charter(
    project_id: int,
    charter_in: CharterCreate,
    current_user: User = Depends(require_roles(["SPONSOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find highest current version
    latest_charter = db.query(Charter).filter(Charter.project_id == project_id).order_by(Charter.version.desc()).first()
    next_version = (latest_charter.version + 1) if latest_charter else 1

    content_raw = (
        f"{project.engagement_model}|{charter_in.rewards}|{charter_in.scope}|"
        f"{charter_in.ip_terms}|{charter_in.confidentiality}|{charter_in.exit_terms}|"
        f"{charter_in.commercialisation}"
    )
    content_hash = hashlib.sha256(content_raw.encode("utf-8")).hexdigest()

    charter = Charter(
        project_id=project_id,
        version=next_version,
        engagement_model=project.engagement_model,
        rewards=charter_in.rewards,
        scope=charter_in.scope,
        ip_terms=charter_in.ip_terms,
        confidentiality=charter_in.confidentiality,
        split_rules=charter_in.split_rules or {},
        credit_rules=charter_in.credit_rules or {},
        exit_terms=charter_in.exit_terms,
        commercialisation=charter_in.commercialisation,
        content_hash=content_hash
    )
    db.add(charter)
    db.commit()
    db.refresh(charter)

    action = "CHARTER_PUBLISHED" if next_version == 1 else "CHARTER_VERSION_CHANGED"
    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        project_id=project_id,
        action=action,
        reason=f"Charter v{next_version} published for project {project_id} ({content_hash[:10]}...)",
        payload_hash=content_hash
    )

    return charter

@router.get("/projects/{project_id}/charters", response_model=List[CharterResponse])
def get_charters(project_id: int, db: Session = Depends(get_db)):
    charters = db.query(Charter).filter(Charter.project_id == project_id).order_by(Charter.version.desc()).all()
    return charters

@router.post("/charters/{charter_id}/accept")
def accept_charter(
    charter_id: int,
    request: CharterAcceptanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    charter = db.query(Charter).filter(Charter.id == charter_id).first()
    if not charter:
        raise HTTPException(status_code=404, detail="Charter not found")

    if not request.model_ack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must separately acknowledge the engagement model before accepting the charter."
        )

    # Check if already accepted
    existing = db.query(CharterAcceptance).filter(
        CharterAcceptance.user_id == current_user.id,
        CharterAcceptance.charter_id == charter_id
    ).first()

    if not existing:
        acceptance = CharterAcceptance(
            user_id=current_user.id,
            charter_id=charter_id,
            version_hash=charter.content_hash,
            model_ack=request.model_ack
        )
        db.add(acceptance)
        db.commit()

    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        project_id=charter.project_id,
        action="CHARTER_ACCEPTED",
        decision="ALLOW",
        reason=f"User {current_user.name} accepted charter v{charter.version} with engagement model ack",
        payload_hash=charter.content_hash
    )

    return {"status": "accepted", "charter_id": charter_id, "version": charter.version, "model_ack": True}

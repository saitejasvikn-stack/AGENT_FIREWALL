import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from db import get_db
from models import User, Project, Milestone, Escrow, Contribution, Agent
from schemas import MilestoneCreate, MilestoneResponse, ContributionResponse
from security import get_current_user, require_roles
from services.ledger_service import ledger_service
from services.scoping import scoping_service
from services.similarity import similarity_service

router = APIRouter(tags=["milestones"])

@router.post("/projects/{project_id}/scope", response_model=List[MilestoneResponse])
def scope_project(
    project_id: int,
    current_user: User = Depends(require_roles(["SPONSOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    milestones = scoping_service.propose_milestones(db=db, project=project, sponsor=current_user)

    ledger_service.append(
        db=db,
        actor_type="agent",
        actor_id=1,  # Scoping Agent
        human_owner_id=current_user.id,
        project_id=project_id,
        action="MILESTONES_PROPOSED",
        reason=f"Scoping agent proposed {len(milestones)} milestones for project {project_id}"
    )

    return milestones

@router.post("/projects/{project_id}/milestones/accept")
def accept_milestones(
    project_id: int,
    current_user: User = Depends(require_roles(["SPONSOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    milestones = db.query(Milestone).filter(Milestone.project_id == project_id).all()
    for m in milestones:
        if m.status == "PROPOSED":
            m.status = "ACCEPTED"
    db.commit()

    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        project_id=project_id,
        action="MILESTONES_ACCEPTED",
        reason=f"Sponsor accepted milestones for project {project_id}"
    )

    return {"status": "accepted", "project_id": project_id, "count": len(milestones)}

@router.post("/milestones/{milestone_id}/fund")
def fund_milestone(
    milestone_id: int,
    current_user: User = Depends(require_roles(["SPONSOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if milestone.project.engagement_model not in ["FUNDED", "STIPEND"]:
        raise HTTPException(status_code=400, detail="Milestone project is not funded")

    amount = milestone.budget_inr or milestone.project.budget_inr or 100000

    existing_escrow = db.query(Escrow).filter(Escrow.milestone_id == milestone_id).first()
    if not existing_escrow:
        escrow = Escrow(
            milestone_id=milestone_id,
            amount=amount,
            status="HELD",
            fee_pct=10.0,
            ai_reserve_pct=5.0
        )
        db.add(escrow)
    else:
        existing_escrow.status = "HELD"
        escrow = existing_escrow

    milestone.status = "FUNDED"
    db.commit()

    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        project_id=milestone.project_id,
        action="ESCROW_FUNDED",
        reason=f"Escrow funded with Rs {amount} for milestone {milestone_id} (status: HELD)"
    )

    return {"status": "HELD", "milestone_id": milestone_id, "amount": amount}

@router.post("/milestones/{milestone_id}/submissions", response_model=ContributionResponse)
def submit_work(
    milestone_id: int,
    title: str = Form(...),
    content_text: str = Form(...),
    ai_share_pct: float = Form(0.0),
    ai_agent_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # Calculate SHA-256 artefact hash
    artefact_hash = hashlib.sha256(f"{title}:{content_text}".encode("utf-8")).hexdigest()

    # Similarity check
    sim_score = similarity_service.check_similarity(db=db, content_text=content_text)
    initial_status = "FLAGGED" if sim_score >= 0.35 else "SUBMITTED"

    contribution = Contribution(
        milestone_id=milestone_id,
        author_id=current_user.id,
        title=title,
        content_text=content_text,
        artefact_hash=artefact_hash,
        ai_share_pct=ai_share_pct,
        ai_agent_id=ai_agent_id,
        similarity_score=sim_score,
        status=initial_status
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)

    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        project_id=milestone.project_id,
        action="SUBMISSION_CREATED",
        payload_hash=artefact_hash,
        reason=f"Submission '{title}' created (AI: {ai_share_pct}%, similarity: {sim_score:.2f})"
    )

    if initial_status == "FLAGGED":
        ledger_service.append(
            db=db,
            actor_type="system",
            actor_id=0,
            project_id=milestone.project_id,
            action="SIMILARITY_FLAGGED",
            decision="APPROVAL",
            reason=f"Submission {contribution.id} flagged for high similarity ({sim_score:.2f} >= 0.35)"
        )

    return contribution

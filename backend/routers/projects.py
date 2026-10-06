from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from db import get_db
from models import User, Project, Charter, CharterAcceptance
from schemas import ProjectCreate, ProjectResponse
from security import get_current_user, require_roles
from services.ledger_service import ledger_service

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    # Mask confidential brief in general list
    result = []
    for p in projects:
        p_dict = ProjectResponse.model_validate(p)
        if p.sensitivity == "CONFIDENTIAL":
            p_dict.confidential_brief = "[CONFIDENTIAL - ACCEPT CHARTER TO VIEW]"
        result.append(p_dict)
    return result

@router.post("", response_model=ProjectResponse)
def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(require_roles(["SPONSOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    project = Project(
        sponsor_id=current_user.id,
        title=project_in.title,
        public_summary=project_in.public_summary,
        confidential_brief=project_in.confidential_brief,
        sensitivity=project_in.sensitivity,
        engagement_model=project_in.engagement_model,
        status="OPEN",
        budget_inr=project_in.budget_inr
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        project_id=project.id,
        action="PROJECT_POSTED",
        reason=f"Project '{project.title}' posted ({project.engagement_model}, {project.sensitivity})"
    )

    return project

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Access check for confidential project brief
    if project.sensitivity == "CONFIDENTIAL":
        is_sponsor = project.sponsor_id == current_user.id
        is_admin = current_user.role == "ADMIN"
        
        # Check if user accepted latest charter
        latest_charter = db.query(Charter).filter(Charter.project_id == project_id).order_by(Charter.version.desc()).first()
        has_accepted = False
        if latest_charter:
            acceptance = db.query(CharterAcceptance).filter(
                CharterAcceptance.user_id == current_user.id,
                CharterAcceptance.charter_id == latest_charter.id
            ).first()
            if acceptance:
                has_accepted = True

        if not (is_sponsor or is_admin or has_accepted):
            # Log denied access
            ledger_service.append(
                db=db,
                actor_type="human",
                actor_id=current_user.id,
                project_id=project.id,
                action="BRIEF_ACCESS_DENIED",
                decision="BLOCK",
                reason=f"User {current_user.name} ({current_user.id}) denied confidential brief access for project {project_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You must accept the project charter before accessing confidential brief."
            )

        # Log allowed access
        ledger_service.append(
            db=db,
            actor_type="human",
            actor_id=current_user.id,
            project_id=project.id,
            action="BRIEF_ACCESS_ALLOWED",
            decision="ALLOW",
            reason=f"User {current_user.name} ({current_user.id}) accessed confidential brief for project {project_id}"
        )

    return project

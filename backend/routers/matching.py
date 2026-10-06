from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from security import get_current_user
from services.matching import matching_service

router = APIRouter(prefix="/projects", tags=["matching"])

@router.get("/{project_id}/matches")
def get_project_matches(
    project_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return matching_service.match_team(db=db, project_id=project_id)

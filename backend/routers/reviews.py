from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models import User, Contribution, Review
from schemas import ReviewCreate
from security import get_current_user, require_roles
from services.ledger_service import ledger_service

router = APIRouter(tags=["reviews"])

@router.post("/contributions/{contribution_id}/review")
def review_contribution(
    contribution_id: int,
    review_in: ReviewCreate,
    current_user: User = Depends(require_roles(["EXPERT", "ADMIN"])),
    db: Session = Depends(get_db)
):
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    review = Review(
        contribution_id=contribution_id,
        reviewer_id=current_user.id,
        impact_score=review_in.impact_score,
        verdict=review_in.verdict,
        reason=review_in.reason,
        coi_declared=review_in.coi_declared or False
    )
    db.add(review)

    if review_in.verdict == "ACCEPT":
        contribution.status = "ACCEPTED"
    elif review_in.verdict == "REJECT":
        contribution.status = "REJECTED"

    db.commit()

    ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        project_id=contribution.milestone.project_id,
        action="REVIEW_SUBMITTED",
        decision=review_in.verdict,
        reason=f"Expert review on contribution #{contribution_id}: impact score {review_in.impact_score}/10 ({review_in.verdict})"
    )

    return {"status": "reviewed", "verdict": review_in.verdict, "impact_score": review_in.impact_score}

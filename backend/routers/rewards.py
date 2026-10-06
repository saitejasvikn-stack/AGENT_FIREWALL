from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from db import get_db
from models import Milestone, Contribution, Review, Payout, Escrow, User, Credential
from security import get_current_user, require_roles
from services.ledger_service import ledger_service
from services.reward_engine import reward_engine
from services.credentials import credential_service

router = APIRouter(tags=["rewards"])

@router.post("/milestones/{milestone_id}/settle")
def settle_milestone(
    milestone_id: int,
    current_user: User = Depends(require_roles(["SPONSOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    project = milestone.project

    # Find accepted contributions for milestone
    accepted_contributions = db.query(Contribution).filter(
        Contribution.milestone_id == milestone_id,
        Contribution.status == "ACCEPTED"
    ).all()

    # Calculate student impact scores
    student_scores: Dict[int, float] = {}
    for c in accepted_contributions:
        reviews = db.query(Review).filter(Review.contribution_id == c.id).all()
        for r in reviews:
            student_scores[c.author_id] = student_scores.get(c.author_id, 0.0) + r.impact_score

    total_score = sum(student_scores.values())
    student_weights: Dict[int, float] = {}

    if total_score > 0:
        for uid, score in student_scores.items():
            student_weights[uid] = score / total_score
    else:
        # Default equal weights if no scores yet
        student_users = db.query(User).filter(User.role == "STUDENT").limit(3).all()
        if student_users:
            eq_w = 1.0 / len(student_users)
            for u in student_users:
                student_weights[u.id] = eq_w

    expert_user = db.query(User).filter(User.role == "EXPERT").first()
    expert_id = expert_user.id if expert_user else None

    is_funded = project.engagement_model in ["FUNDED", "STIPEND"]

    if is_funded:
        escrow = db.query(Escrow).filter(Escrow.milestone_id == milestone_id).first()
        if not escrow or escrow.status != "HELD":
            raise HTTPException(status_code=409, detail="Escrow must be HELD before settling funded milestone")

        budget = escrow.amount
        result = reward_engine.calculate_money_payout(
            milestone_budget=budget,
            student_weights=student_weights,
            fee_pct=escrow.fee_pct,
            ai_reserve_pct=escrow.ai_reserve_pct,
            expert_user_id=expert_id
        )

        # Release escrow
        escrow.status = "RELEASED"

        # Create payouts
        created_payouts = []
        for uid, amount in result["student_payouts"].items():
            entry = ledger_service.append(
                db=db,
                actor_type="system",
                actor_id=0,
                project_id=project.id,
                action="PAYOUT_RELEASED",
                reason=f"Released monetary payout Rs {amount} to user #{uid}"
            )

            payout = Payout(
                milestone_id=milestone_id,
                user_id=uid,
                kind="MONEY",
                weight=student_weights.get(uid, 0.0),
                amount_inr=amount,
                escrow_id=escrow.id,
                explanation_json=result["explanations"][uid],
                ledger_ref=entry.entry_id
            )
            db.add(payout)
            created_payouts.append(payout)

        if expert_id:
            entry = ledger_service.append(
                db=db,
                actor_type="system",
                actor_id=0,
                project_id=project.id,
                action="PAYOUT_RELEASED",
                reason=f"Released expert fee Rs {result['expert_share']} to expert #{expert_id}"
            )
            expert_payout = Payout(
                milestone_id=milestone_id,
                user_id=expert_id,
                kind="MONEY",
                weight=0.0,
                amount_inr=result["expert_share"],
                escrow_id=escrow.id,
                explanation_json={"role": "expert", "expert_fee": result["expert_share"]},
                ledger_ref=entry.entry_id
            )
            db.add(expert_payout)

        milestone.status = "COMPLETED"
        db.commit()

        return {"status": "RELEASED", "kind": "MONEY", "summary": result}

    else:
        # KNOWLEDGE / INSTITUTIONAL -> CREDIT MODE
        result = reward_engine.calculate_credit_payout(
            credit_pool_cu=milestone.credit_pool_cu,
            student_weights=student_weights
        )

        # Create Credit Payouts
        for uid, cu in result["student_payouts_cu"].items():
            entry = ledger_service.append(
                db=db,
                actor_type="system",
                actor_id=0,
                project_id=project.id,
                action="CREDIT_ISSUED",
                reason=f"Issued {cu} Credit Units to user #{uid}"
            )
            payout = Payout(
                milestone_id=milestone_id,
                user_id=uid,
                kind="CREDIT",
                weight=student_weights.get(uid, 0.0),
                credit_cu=cu,
                explanation_json=result["explanations"][uid],
                ledger_ref=entry.entry_id
            )
            db.add(payout)

        # Issue Credentials
        credentials = credential_service.issue_credentials_for_project(
            db=db,
            project_id=project.id,
            student_cu_map=result["student_payouts_cu"],
            expert_user_id=expert_id
        )

        milestone.status = "COMPLETED"
        db.commit()

        return {"status": "RELEASED", "kind": "CREDIT", "summary": result, "credentials_issued": len(credentials)}

@router.get("/payouts/{payout_id}/explain")
def explain_payout(
    payout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    return {
        "payout_id": payout.id,
        "kind": payout.kind,
        "amount_inr": payout.amount_inr,
        "credit_cu": payout.credit_cu,
        "explanation": payout.explanation_json,
        "ledger_ref": payout.ledger_ref
    }

@router.get("/verify/{code}")
def public_verify_credential(code: str, db: Session = Depends(get_db)):
    return credential_service.verify_credential(db=db, verify_code=code)

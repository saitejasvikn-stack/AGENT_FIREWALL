from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from db import get_db
from models import User, LedgerEntry, Agent
from schemas import ToolRequestPayload, FirewallEvaluationResponse, ApprovalDecisionRequest
from security import get_current_user
from services.firewall_service import firewall_service
from services.ledger_service import ledger_service

router = APIRouter(tags=["firewall"])

@router.post("/firewall/evaluate", response_model=FirewallEvaluationResponse)
def evaluate_tool_request(
    payload: ToolRequestPayload,
    db: Session = Depends(get_db)
):
    return firewall_service.evaluate(db=db, request=payload)

@router.get("/firewall/receipts")
def get_firewall_receipts(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(LedgerEntry).filter(LedgerEntry.action == "AGENT_TOOL_REQUEST")
    if project_id:
        query = query.filter(LedgerEntry.project_id == project_id)
    entries = query.order_by(LedgerEntry.entry_id.desc()).all()
    return entries

@router.get("/approvals")
def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find tool requests requiring APPROVAL for agents owned by current_user
    my_agents = db.query(Agent.id).filter(Agent.owner_user_id == current_user.id).all()
    my_agent_ids = [a[0] for a in my_agents]

    approvals = db.query(LedgerEntry).filter(
        LedgerEntry.action == "AGENT_TOOL_REQUEST",
        LedgerEntry.decision == "APPROVAL",
        LedgerEntry.actor_id.in_(my_agent_ids) if my_agent_ids else False
    ).order_by(LedgerEntry.entry_id.desc()).all()

    return approvals

@router.post("/approvals/{entry_id}/decision")
def decide_approval(
    entry_id: int,
    request: ApprovalDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    original_entry = db.query(LedgerEntry).filter(LedgerEntry.entry_id == entry_id).first()
    if not original_entry:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if request.decision not in ["APPROVE", "DENY"]:
        raise HTTPException(status_code=400, detail="Decision must be APPROVE or DENY")

    action = "APPROVAL_GRANTED" if request.decision == "APPROVE" else "APPROVAL_DENIED"

    new_entry = ledger_service.append(
        db=db,
        actor_type="human",
        actor_id=current_user.id,
        human_owner_id=current_user.id,
        project_id=original_entry.project_id,
        action=action,
        decision=request.decision,
        reason=f"Human owner {current_user.name} ({request.decision}) for agent tool request #{entry_id}"
    )

    return {"status": request.decision, "ledger_entry_id": new_entry.entry_id}

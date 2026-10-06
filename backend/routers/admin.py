from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models import User, Project, Contribution, LedgerEntry, Dispute
from security import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats")
def get_admin_stats(
    current_user = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    return {
        "users_count": db.query(User).count(),
        "projects_count": db.query(Project).count(),
        "contributions_count": db.query(Contribution).count(),
        "ledger_entries_count": db.query(LedgerEntry).count(),
        "open_disputes_count": db.query(Dispute).filter(Dispute.status == "OPEN").count()
    }

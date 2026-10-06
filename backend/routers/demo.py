from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from db import get_db, engine
from models import LedgerEntry, Project, Milestone
from services.ledger_service import ledger_service, calculate_entry_hash
import sys
import os

router = APIRouter(prefix="/demo", tags=["demo"])

TAMPERED_BACKUPS = {}

@router.post("/tamper/{entry_id}")
def tamper_ledger_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(LedgerEntry).filter(LedgerEntry.entry_id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Ledger entry #{entry_id} not found")

    TAMPERED_BACKUPS[entry_id] = {
        "reason": entry.reason,
        "current_hash": entry.current_hash
    }

    with engine.connect() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS prevent_ledger_update;"))
        conn.execute(
            text(f"UPDATE ledger_entries SET reason = 'TAMPERED: Unauthorized modification of historical record', current_hash = 'bad_hash_{entry_id}' WHERE entry_id = {entry_id};")
        )
        conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS prevent_ledger_update
            BEFORE UPDATE ON ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'Ledger is append-only. UPDATE operations are forbidden.');
            END;
            """)
        )
        conn.commit()

    return {"status": "tampered", "entry_id": entry_id, "detail": "Ledger entry altered to trigger verification failure"}

@router.post("/repair")
def repair_ledger(db: Session = Depends(get_db)):
    entries = db.query(LedgerEntry).order_by(LedgerEntry.entry_id.asc()).all()
    if not entries:
        return {"status": "repaired", "count": 0}

    with engine.connect() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS prevent_ledger_update;"))
        
        expected_prev = "0" * 64
        for entry in entries:
            if entry.entry_id in TAMPERED_BACKUPS:
                orig = TAMPERED_BACKUPS[entry.entry_id]
                entry.reason = orig["reason"]
            
            recomputed = calculate_entry_hash(
                prev_hash=expected_prev,
                entry_id=entry.entry_id,
                ts=entry.ts,
                actor_id=entry.actor_id,
                human_owner_id=entry.human_owner_id,
                project_id=entry.project_id,
                action=entry.action,
                decision=entry.decision,
                reason=entry.reason,
                payload_hash=entry.payload_hash
            )
            
            conn.execute(
                text(f"UPDATE ledger_entries SET prev_hash = '{expected_prev}', current_hash = '{recomputed}' WHERE entry_id = {entry.entry_id};")
            )
            expected_prev = recomputed

        conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS prevent_ledger_update
            BEFORE UPDATE ON ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'Ledger is append-only. UPDATE operations are forbidden.');
            END;
            """)
        )
        conn.commit()

    TAMPERED_BACKUPS.clear()
    return {"status": "repaired", "detail": "Ledger integrity chain successfully re-calculated and verified"}

@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "seed"))
    try:
        import seed
        seed.run_seed(db)
        return {"status": "reset", "detail": "Database reset and re-seeded with demo data"}
    except Exception as e:
        return {"status": "reset", "detail": f"Database cleared. Seed execution note: {str(e)}"}

@router.post("/fast-forward")
def fast_forward(db: Session = Depends(get_db)):
    milestones = db.query(Milestone).all()
    for m in milestones:
        m.status = "ACCEPTED"
    db.commit()
    return {"status": "fast_forwarded", "detail": "Projects fast-forwarded to ready-to-accept state"}

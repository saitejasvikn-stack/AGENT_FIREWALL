import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from models import LedgerEntry

GENESIS_PREV_HASH = "0" * 64

def calculate_entry_hash(
    prev_hash: str,
    entry_id: int,
    ts: str,
    actor_id: int,
    human_owner_id: int | None,
    project_id: int | None,
    action: str,
    decision: str | None,
    reason: str | None,
    payload_hash: str
) -> str:
    raw_data = (
        f"{prev_hash}"
        f"{entry_id}"
        f"{ts}"
        f"{actor_id}"
        f"{human_owner_id if human_owner_id is not None else ''}"
        f"{project_id if project_id is not None else ''}"
        f"{action}"
        f"{decision or ''}"
        f"{reason or ''}"
        f"{payload_hash}"
    )
    return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

class LedgerService:
    @staticmethod
    def append(
        db: Session,
        actor_type: str,
        actor_id: int,
        action: str,
        human_owner_id: int | None = None,
        project_id: int | None = None,
        decision: str | None = None,
        reason: str | None = None,
        payload_hash: str | None = None
    ) -> LedgerEntry:
        # Get last entry for prev_hash
        last_entry = db.query(LedgerEntry).order_by(LedgerEntry.entry_id.desc()).first()
        prev_hash = last_entry.current_hash if last_entry else GENESIS_PREV_HASH
        
        # Next entry ID
        next_id = (last_entry.entry_id + 1) if last_entry else 1
        ts = datetime.utcnow().isoformat()
        if not payload_hash:
            payload_hash = hashlib.sha256(f"{action}:{ts}".encode("utf-8")).hexdigest()

        current_hash = calculate_entry_hash(
            prev_hash=prev_hash,
            entry_id=next_id,
            ts=ts,
            actor_id=actor_id,
            human_owner_id=human_owner_id,
            project_id=project_id,
            action=action,
            decision=decision,
            reason=reason,
            payload_hash=payload_hash
        )

        entry = LedgerEntry(
            entry_id=next_id,
            ts=ts,
            actor_type=actor_type,
            actor_id=actor_id,
            human_owner_id=human_owner_id,
            project_id=project_id,
            action=action,
            decision=decision,
            reason=reason,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            current_hash=current_hash
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def verify(db: Session) -> dict:
        entries = db.query(LedgerEntry).order_by(LedgerEntry.entry_id.asc()).all()
        if not entries:
            return {"ok": True, "head_hash": GENESIS_PREV_HASH, "count": 0}

        expected_prev_hash = GENESIS_PREV_HASH

        for entry in entries:
            # 1. Check prev_hash linkage
            if entry.prev_hash != expected_prev_hash:
                return {
                    "ok": False,
                    "entry_id": entry.entry_id,
                    "error": "CHAIN_BROKEN",
                    "reason": f"Entry {entry.entry_id} prev_hash '{entry.prev_hash[:10]}...' does not match expected '{expected_prev_hash[:10]}...'"
                }

            # 2. Check current_hash integrity
            computed_hash = calculate_entry_hash(
                prev_hash=entry.prev_hash,
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

            if computed_hash != entry.current_hash:
                return {
                    "ok": False,
                    "entry_id": entry.entry_id,
                    "error": "HASH_MISMATCH",
                    "reason": f"Entry {entry.entry_id} hash mismatch. DB value: '{entry.current_hash[:10]}...', Computed: '{computed_hash[:10]}...'"
                }

            expected_prev_hash = entry.current_hash

        return {
            "ok": True,
            "head_hash": entries[-1].current_hash,
            "count": len(entries)
        }

ledger_service = LedgerService()

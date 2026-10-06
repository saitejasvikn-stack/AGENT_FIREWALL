from sqlalchemy.orm import Session
from models import Escrow, Milestone

class EscrowMockService:
    @staticmethod
    def fund_escrow(db: Session, milestone_id: int, amount: int) -> Escrow:
        escrow = db.query(Escrow).filter(Escrow.milestone_id == milestone_id).first()
        if not escrow:
            escrow = Escrow(
                milestone_id=milestone_id,
                amount=amount,
                status="HELD",
                fee_pct=10.0,
                ai_reserve_pct=5.0
            )
            db.add(escrow)
        else:
            escrow.status = "HELD"
            escrow.amount = amount

        milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
        if milestone:
            milestone.status = "FUNDED"

        db.commit()
        db.refresh(escrow)
        return escrow

escrow_mock_service = EscrowMockService()

import uuid
from sqlalchemy.orm import Session
from models import Credential, User, Project, LedgerEntry
from services.ledger_service import ledger_service

class CredentialService:
    @staticmethod
    def issue_credentials_for_project(
        db: Session,
        project_id: int,
        student_cu_map: dict[int, float],
        expert_user_id: int | None
    ) -> list[Credential]:
        created_credentials = []

        # Sort students by CU rank descending for author order
        sorted_students = sorted(student_cu_map.items(), key=lambda x: x[1], reverse=True)

        for rank, (user_id, cu) in enumerate(sorted_students, start=1):
            cred_type = "CERTIFICATE"
            if cu >= 30.0:
                cred_type = "COAUTHOR"  # Lead Contributor
            elif cu >= 10.0:
                cred_type = "CERTIFICATE"  # Contributor

            verify_code = f"AF-CRED-{uuid.uuid4().hex[:8].upper()}"

            entry = ledger_service.append(
                db=db,
                actor_type="system",
                actor_id=0,
                project_id=project_id,
                action="CREDENTIAL_ISSUED",
                reason=f"Issued {cred_type} to user {user_id} ({cu} CU, rank #{rank})"
            )

            cred = Credential(
                user_id=user_id,
                project_id=project_id,
                type=cred_type,
                author_order=rank,
                credit_cu=cu,
                verify_code=verify_code,
                ledger_ref=entry.entry_id
            )
            db.add(cred)
            created_credentials.append(cred)

        if expert_user_id:
            verify_code = f"AF-CRED-EXP-{uuid.uuid4().hex[:8].upper()}"
            entry = ledger_service.append(
                db=db,
                actor_type="system",
                actor_id=0,
                project_id=project_id,
                action="CREDENTIAL_ISSUED",
                reason=f"Issued MENTOR_LETTER & BADGE to expert {expert_user_id}"
            )

            cred = Credential(
                user_id=expert_user_id,
                project_id=project_id,
                type="MENTOR_LETTER",
                author_order=0,  # Corresponding Author
                credit_cu=20.0,
                verify_code=verify_code,
                ledger_ref=entry.entry_id
            )
            db.add(cred)
            created_credentials.append(cred)

        db.commit()
        return created_credentials

    @staticmethod
    def verify_credential(db: Session, verify_code: str) -> dict:
        cred = db.query(Credential).filter(Credential.verify_code == verify_code).first()
        if not cred:
            return {"status": "INVALID", "detail": "Credential code not found"}

        if cred.revoked_by_entry:
            return {"status": "REVOKED", "detail": f"Credential revoked in ledger entry #{cred.revoked_by_entry}"}

        # Check ledger integrity
        ledger_verification = ledger_service.verify(db)
        if not ledger_verification["ok"]:
            return {
                "status": "TAMPERED",
                "detail": f"Ledger integrity check failed: {ledger_verification['error']}",
                "credential": {
                    "code": cred.verify_code,
                    "user_name": cred.user.name if cred.user else "Unknown",
                    "project_title": cred.project.title if cred.project else "Unknown",
                    "type": cred.type
                }
            }

        return {
            "status": "VALID",
            "credential": {
                "code": cred.verify_code,
                "user_name": cred.user.name if cred.user else "Unknown",
                "project_title": cred.project.title if cred.project else "Unknown",
                "type": cred.type,
                "author_order": cred.author_order,
                "credit_cu": cred.credit_cu,
                "created_at": cred.created_at.isoformat() if cred.created_at else ""
            },
            "ledger_ref": cred.ledger_ref
        }

credential_service = CredentialService()

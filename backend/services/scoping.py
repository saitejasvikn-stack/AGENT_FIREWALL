from sqlalchemy.orm import Session
from models import Milestone, Project, User

class ScopingService:
    @staticmethod
    def propose_milestones(db: Session, project: Project, sponsor: User) -> list[Milestone]:
        existing = db.query(Milestone).filter(Milestone.project_id == project.id).all()
        if existing:
            return existing

        m1 = Milestone(
            project_id=project.id,
            title="Milestone 1: Model Architecture & Preprocessing Pipeline",
            deliverable="Edge-optimized CNN model architecture and dataset preprocessing script",
            acceptance_criteria="Model size < 15MB, preprocessing latency < 50ms, validation accuracy >= 88%",
            skills_required=["PyTorch", "Medical Imaging", "Edge Deployment"],
            type="NORMAL",
            budget_inr=100000 if project.engagement_model in ["FUNDED", "STIPEND"] else None,
            credit_pool_cu=100.0,
            status="PROPOSED"
        )

        m2 = Milestone(
            project_id=project.id,
            title="Milestone 2: Validation, Benchmarking & Exploratory Edge Deployment",
            deliverable="Edge device latency benchmarks and error mode analysis report",
            acceptance_criteria="Tested on ARM edge platform, comprehensive failure analysis documented",
            skills_required=["PyTorch", "Edge Deployment", "Benchmarking"],
            type="EXPLORATION",
            budget_inr=None,
            credit_pool_cu=100.0,
            status="PROPOSED"
        )

        db.add(m1)
        db.add(m2)
        db.commit()
        db.refresh(m1)
        db.refresh(m2)
        return [m1, m2]

scoping_service = ScopingService()

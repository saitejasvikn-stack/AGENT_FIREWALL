import os
import sys
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db import Base, engine, SessionLocal, setup_ledger_triggers
from models import User, Project, Charter, Milestone, Agent, LedgerEntry
from security import get_password_hash
from services.ledger_service import ledger_service

def run_seed(db: Session = None):
    close_at_end = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        setup_ledger_triggers()
        db = SessionLocal()
        close_at_end = True

    try:
        with engine.connect() as conn:
            conn.execute(text("DROP TRIGGER IF EXISTS prevent_ledger_update;"))
            conn.execute(text("DROP TRIGGER IF EXISTS prevent_ledger_delete;"))
            conn.execute(text("DELETE FROM credentials;"))
            conn.execute(text("DELETE FROM payouts;"))
            conn.execute(text("DELETE FROM reviews;"))
            conn.execute(text("DELETE FROM contributions;"))
            conn.execute(text("DELETE FROM escrows;"))
            conn.execute(text("DELETE FROM agents;"))
            conn.execute(text("DELETE FROM charter_acceptances;"))
            conn.execute(text("DELETE FROM milestones;"))
            conn.execute(text("DELETE FROM charters;"))
            conn.execute(text("DELETE FROM projects;"))
            conn.execute(text("DELETE FROM ledger_entries;"))
            conn.execute(text("DELETE FROM users;"))
            conn.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS prevent_ledger_update
                BEFORE UPDATE ON ledger_entries
                BEGIN
                    SELECT RAISE(ABORT, 'Ledger is append-only. UPDATE operations are forbidden.');
                END;
                """)
            )
            conn.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS prevent_ledger_delete
                BEFORE DELETE ON ledger_entries
                BEGIN
                    SELECT RAISE(ABORT, 'Ledger is append-only. DELETE operations are forbidden.');
                END;
                """)
            )
            conn.commit()

        demo_password_hash = get_password_hash("demo123")

        # 1. Seed Users
        sponsor = User(
            name="Dr. Anita Rao",
            email="anita@medivision.org",
            password_hash=demo_password_hash,
            role="SPONSOR",
            verification_level="L2",
            institution="MediVision Labs",
            skills=["Medical Imaging", "Project Management"],
            conflicts=[]
        )
        expert1 = User(
            name="Prof. Kiran Shah",
            email="kiran@iisc.ac.in",
            password_hash=demo_password_hash,
            role="EXPERT",
            verification_level="L2",
            institution="Indian Institute of Science",
            skills=["PyTorch", "Medical Imaging", "Computer Vision"],
            conflicts=[]
        )
        expert2 = User(
            name="Dr. Rohan Mehta",
            email="rohan@medivision-competitor.com",
            password_hash=demo_password_hash,
            role="EXPERT",
            verification_level="L2",
            institution="MediVision Competitor Corp",
            skills=["PyTorch", "Edge Deployment"],
            conflicts=["MediVision Labs"]  # Rohan has COI
        )
        student1 = User(
            name="Priya",
            email="priya@student.edu",
            password_hash=demo_password_hash,
            role="STUDENT",
            verification_level="L2",
            institution="IIT Madras",
            skills=["PyTorch", "Medical Imaging", "Edge Deployment"],
            conflicts=[]
        )
        student2 = User(
            name="Arun",
            email="arun@student.edu",
            password_hash=demo_password_hash,
            role="STUDENT",
            verification_level="L1",
            institution="NIT Surathkal",
            skills=["PyTorch", "Medical Imaging", "Benchmarking"],
            conflicts=[]
        )
        student3 = User(
            name="Meera",
            email="meera@student.edu",
            password_hash=demo_password_hash,
            role="STUDENT",
            verification_level="L1",
            institution="PES University",
            skills=["PyTorch", "Edge Deployment", "Benchmarking"],
            conflicts=[]
        )
        admin = User(
            name="Admin",
            email="admin@agentfirewall.org",
            password_hash=demo_password_hash,
            role="ADMIN",
            verification_level="L2",
            institution="Agent Firewall Core",
            skills=["Auditing", "Governance"],
            conflicts=[]
        )

        db.add_all([sponsor, expert1, expert2, student1, student2, student3, admin])
        db.commit()

        for u in [sponsor, expert1, expert2, student1, student2, student3, admin]:
            ledger_service.append(
                db=db,
                actor_type="human",
                actor_id=u.id,
                action="USER_REGISTERED",
                reason=f"Seeded user {u.name} ({u.role})"
            )

        # 2. Seed Project A (FUNDED, CONFIDENTIAL)
        proj_a = Project(
            sponsor_id=sponsor.id,
            title="Low-cost detection of diabetic retinopathy from fundus images on edge devices",
            public_summary="Developing lightweight AI models to detect diabetic retinopathy from retinal fundus images for low-cost handheld edge diagnostic devices in rural clinics.",
            confidential_brief="""CONFIDENTIAL BRIEF — MEDIVISION LABS
Dataset Location: /data/medivision/fundus_raw_v2.tar.gz
Hardware Constraint: Must execute on ARM Cortex-A53 edge board with <15MB RAM footprint.
Target Clinical Performance: 92% sensitivity on Grade 3+ Diabetic Retinopathy.
Proprietary Preprocessing Filter: Apply CLAHE contrast enhancement with tile_grid=(8,8).

[POISONED INJECTION ATTACHMENT INCLUDED IN RESEARCH DOCS]""",
            sensitivity="CONFIDENTIAL",
            engagement_model="FUNDED",
            status="OPEN",
            budget_inr=100000
        )
        db.add(proj_a)
        db.commit()

        ledger_service.append(
            db=db,
            actor_type="human",
            actor_id=sponsor.id,
            project_id=proj_a.id,
            action="PROJECT_POSTED",
            reason=f"Posted funded confidential project #{proj_a.id} (Rs 1,00,000)"
        )

        charter_a_content = "FUNDED|Rs 1,00,000 milestone funding + Certificate|Edge CNN model|MediVision Labs retains commercial rights|CONFIDENTIAL: Local Ollama only|Pro-rata split|5% royalty pool"
        charter_a_hash = hashlib.sha256(charter_a_content.encode("utf-8")).hexdigest()

        charter_a = Charter(
            project_id=proj_a.id,
            version=1,
            engagement_model="FUNDED",
            rewards="Rs 1,00,000 milestone funding + Certificate + Lead Contributor co-authorship",
            scope="Milestone 1: Model Architecture & Preprocessing Pipeline\nMilestone 2: Validation, Benchmarking & Edge Deployment",
            ip_terms="MediVision Labs retains commercial rights; contributors retain academic publication credit.",
            confidentiality="CONFIDENTIAL: Local Ollama / Mock model only. External exports prohibited.",
            split_rules={"fee_pct": 10.0, "ai_reserve_pct": 5.0, "expert_pct": 30.0, "student_equal_pct": 40.0},
            credit_rules={"credit_pool_cu": 100.0},
            exit_terms="Leaving midway retains credit for accepted work pro-rata.",
            commercialisation="Royalty pool of 5% net revenue distributed by contribution weights.",
            content_hash=charter_a_hash
        )
        db.add(charter_a)
        db.commit()

        ledger_service.append(
            db=db,
            actor_type="human",
            actor_id=sponsor.id,
            project_id=proj_a.id,
            action="CHARTER_PUBLISHED",
            payload_hash=charter_a_hash,
            reason="Charter v1 published for Project A"
        )

        m1 = Milestone(
            project_id=proj_a.id,
            title="Milestone 1: Model Architecture & Preprocessing Pipeline",
            deliverable="Edge-optimized CNN model architecture and dataset preprocessing script",
            acceptance_criteria="Model size < 15MB, preprocessing latency < 50ms, validation accuracy >= 88%",
            skills_required=["PyTorch", "Medical Imaging", "Edge Deployment"],
            type="NORMAL",
            budget_inr=100000,
            credit_pool_cu=100.0,
            status="PROPOSED"
        )
        m2 = Milestone(
            project_id=proj_a.id,
            title="Milestone 2: Validation, Benchmarking & Exploratory Edge Deployment",
            deliverable="Edge device latency benchmarks and error mode analysis report",
            acceptance_criteria="Tested on ARM edge platform, comprehensive failure analysis documented",
            skills_required=["PyTorch", "Edge Deployment", "Benchmarking"],
            type="EXPLORATION",
            budget_inr=0,
            credit_pool_cu=100.0,
            status="PROPOSED"
        )
        db.add_all([m1, m2])
        db.commit()

        # 3. Seed Project B (KNOWLEDGE, UNPAID)
        proj_b = Project(
            sponsor_id=sponsor.id,
            title="Benchmarking small language models for Kannada text classification",
            public_summary="Evaluating open-source small language models for low-resource Kannada text classification and sentiment analysis tasks.",
            confidential_brief=None,
            sensitivity="PUBLIC",
            engagement_model="KNOWLEDGE",
            status="OPEN",
            budget_inr=None
        )
        db.add(proj_b)
        db.commit()

        ledger_service.append(
            db=db,
            actor_type="human",
            actor_id=sponsor.id,
            project_id=proj_b.id,
            action="PROJECT_POSTED",
            reason=f"Posted knowledge project #{proj_b.id} (UNPAID)"
        )

        charter_b_content = "KNOWLEDGE|100 CU + Badge + Certificate|SLM Benchmark|Open-source MIT|PUBLIC|Pro-rata split|10% pre-declared royalty"
        charter_b_hash = hashlib.sha256(charter_b_content.encode("utf-8")).hexdigest()

        charter_b = Charter(
            project_id=proj_b.id,
            version=1,
            engagement_model="KNOWLEDGE",
            rewards="100 Credit Units (CU), Badge, Mentor letter for top contributors. NO PAYMENT.",
            scope="Milestone 1: Dataset Curation & Model Fine-tuning",
            ip_terms="Open-source MIT licence for public benefit.",
            confidentiality="Public open-science collaboration.",
            split_rules={"expert_pct": 20.0, "student_equal_pct": 30.0},
            credit_rules={"credit_pool_cu": 100.0},
            exit_terms="Open participation model.",
            commercialisation="Pre-declared 10% royalty split if commercialized.",
            content_hash=charter_b_hash
        )
        db.add(charter_b)
        db.commit()

        m_b1 = Milestone(
            project_id=proj_b.id,
            title="Milestone 1: Dataset Curation & Model Fine-tuning",
            deliverable="Kannada sentiment dataset and fine-tuned SLM weights",
            acceptance_criteria="F1 score >= 82% on Kannada sentiment test set",
            skills_required=["PyTorch", "Benchmarking"],
            type="NORMAL",
            budget_inr=None,
            credit_pool_cu=100.0,
            status="PROPOSED"
        )
        db.add(m_b1)
        db.commit()

        # 4. Seed Agents
        scoping_agent = Agent(
            type="SCOPING",
            owner_user_id=sponsor.id,
            project_id=proj_a.id,
            allowed_tools=["draft_milestones"],
            model="mock",
            status="ACTIVE"
        )
        research_agent = Agent(
            type="RESEARCH",
            owner_user_id=student1.id,  # Owned by Priya
            project_id=proj_a.id,
            allowed_tools=["search_docs", "summarize", "similarity_check", "send_email", "export", "publish"],
            model="mock",
            status="ACTIVE"
        )
        reviewer_agent = Agent(
            type="REVIEWER",
            owner_user_id=expert1.id,  # Owned by Prof. Kiran Shah
            project_id=proj_a.id,
            allowed_tools=["similarity_check", "rubric_check", "draft_impact_score"],
            model="mock",
            status="ACTIVE"
        )
        db.add_all([scoping_agent, research_agent, reviewer_agent])
        db.commit()

    finally:
        if close_at_end:
            db.close()

if __name__ == "__main__":
    run_seed()
    print("Idempotent database seeding completed successfully!")

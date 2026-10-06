from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # STUDENT, EXPERT, SPONSOR, ADMIN
    verification_level = Column(String, default="L0")  # L0, L1, L2
    skills = Column(JSON, default=list)
    conflicts = Column(JSON, default=list)
    is_minor = Column(Boolean, default=False)
    institution = Column(String, nullable=True)

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    sponsor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    public_summary = Column(Text, nullable=False)
    confidential_brief = Column(Text, nullable=True)
    sensitivity = Column(String, default="PUBLIC")
    engagement_model = Column(String, nullable=False)
    status = Column(String, default="DRAFT")
    budget_inr = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sponsor = relationship("User", foreign_keys=[sponsor_id])

class Charter(Base):
    __tablename__ = "charters"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, default=1)
    engagement_model = Column(String, nullable=False)
    rewards = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    ip_terms = Column(Text, nullable=False)
    confidentiality = Column(Text, nullable=False)
    split_rules = Column(JSON, default=dict)
    credit_rules = Column(JSON, default=dict)
    exit_terms = Column(Text, nullable=False)
    commercialisation = Column(Text, nullable=False)
    content_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")

class CharterAcceptance(Base):
    __tablename__ = "charter_acceptances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    charter_id = Column(Integer, ForeignKey("charters.id"), nullable=False)
    version_hash = Column(String, nullable=False)
    model_ack = Column(Boolean, default=False)
    ts = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    charter = relationship("Charter")

class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    deliverable = Column(Text, nullable=False)
    acceptance_criteria = Column(Text, nullable=False)
    skills_required = Column(JSON, default=list)
    type = Column(String, default="NORMAL")
    budget_inr = Column(Integer, nullable=True)
    credit_pool_cu = Column(Float, default=100.0)
    status = Column(String, default="PROPOSED")

    project = relationship("Project")

class Escrow(Base):
    __tablename__ = "escrows"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String, default="HELD")
    fee_pct = Column(Float, default=10.0)
    ai_reserve_pct = Column(Float, default=5.0)

    milestone = relationship("Milestone")

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # SCOPING, RESEARCH, REVIEWER
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for testing ownerless agent rejection
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    allowed_tools = Column(JSON, default=list)
    model = Column(String, default="mock")
    status = Column(String, default="ACTIVE")

    owner = relationship("User")
    project = relationship("Project")

class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content_text = Column(Text, nullable=False)
    file_path = Column(String, nullable=True)
    artefact_hash = Column(String, nullable=False)
    ai_share_pct = Column(Float, default=0.0)
    ai_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    similarity_score = Column(Float, nullable=True)
    status = Column(String, default="SUBMITTED")
    created_at = Column(DateTime, default=datetime.utcnow)

    milestone = relationship("Milestone")
    author = relationship("User", foreign_keys=[author_id])
    ai_agent = relationship("Agent", foreign_keys=[ai_agent_id])

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    contribution_id = Column(Integer, ForeignKey("contributions.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    impact_score = Column(Float, nullable=False)
    verdict = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    coi_declared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    contribution = relationship("Contribution")
    reviewer = relationship("User")

class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    amount_inr = Column(Integer, nullable=True)
    credit_cu = Column(Float, nullable=True)
    escrow_id = Column(Integer, ForeignKey("escrows.id"), nullable=True)
    explanation_json = Column(JSON, default=dict)
    ledger_ref = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    milestone = relationship("Milestone")
    user = relationship("User")
    escrow = relationship("Escrow")

class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    type = Column(String, nullable=False)
    author_order = Column(Integer, nullable=True)
    credit_cu = Column(Float, nullable=True)
    verify_code = Column(String, unique=True, index=True, nullable=False)
    ledger_ref = Column(Integer, nullable=False)
    revoked_by_entry = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    project = relationship("Project")

class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    ref_type = Column(String, nullable=False)
    ref_id = Column(Integer, nullable=False)
    raised_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="OPEN")
    resolution = Column(Text, nullable=True)
    ledger_ref = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False)
    actor_type = Column(String, nullable=False)
    actor_id = Column(Integer, nullable=False)
    human_owner_id = Column(Integer, nullable=True)
    project_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    decision = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    payload_hash = Column(String, nullable=False)
    prev_hash = Column(String, nullable=False)
    current_hash = Column(String, nullable=False)

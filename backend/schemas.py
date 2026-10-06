from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# Auth & User
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str  # STUDENT, EXPERT, SPONSOR, ADMIN
    verification_level: Optional[str] = "L0"
    skills: Optional[List[str]] = []
    conflicts: Optional[List[str]] = []
    is_minor: Optional[bool] = False
    institution: Optional[str] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    verification_level: str
    skills: List[str]
    conflicts: List[str]
    is_minor: bool
    institution: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Project
class ProjectCreate(BaseModel):
    title: str
    public_summary: str
    confidential_brief: Optional[str] = None
    sensitivity: str = "PUBLIC"  # PUBLIC, CONFIDENTIAL
    engagement_model: str  # FUNDED, STIPEND, KNOWLEDGE, INSTITUTIONAL
    budget_inr: Optional[int] = None

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sponsor_id: int
    title: str
    public_summary: str
    confidential_brief: Optional[str] = None
    sensitivity: str
    engagement_model: str
    status: str
    budget_inr: Optional[int] = None
    created_at: datetime

# Charter
class CharterCreate(BaseModel):
    rewards: str
    scope: str
    ip_terms: str
    confidentiality: str
    split_rules: Optional[Dict[str, Any]] = {}
    credit_rules: Optional[Dict[str, Any]] = {}
    exit_terms: str
    commercialisation: str

class CharterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: int
    engagement_model: str
    rewards: str
    scope: str
    ip_terms: str
    confidentiality: str
    split_rules: Dict[str, Any]
    credit_rules: Dict[str, Any]
    exit_terms: str
    commercialisation: str
    content_hash: str
    created_at: datetime

class CharterAcceptanceRequest(BaseModel):
    model_ack: bool

# Milestone
class MilestoneCreate(BaseModel):
    title: str
    deliverable: str
    acceptance_criteria: str
    skills_required: List[str]
    type: str = "NORMAL"
    budget_inr: Optional[int] = None
    credit_pool_cu: Optional[float] = 100.0

class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    deliverable: str
    acceptance_criteria: str
    skills_required: List[str]
    type: str
    budget_inr: Optional[int] = None
    credit_pool_cu: float
    status: str

# Firewall & Agents
class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    owner_user_id: int
    project_id: int
    allowed_tools: List[str]
    model: str
    status: str

class ToolRequestPayload(BaseModel):
    agent_id: int
    tool: str
    args: Dict[str, Any]
    project_id: int
    data_labels: Optional[List[str]] = []
    origin_content: Optional[str] = ""
    origin_content_ids: Optional[List[int]] = []
    destination: Optional[str] = "INTERNAL"  # INTERNAL or EXTERNAL
    model_used: Optional[str] = "local"  # local or cloud

class FirewallCheck(BaseModel):
    check_name: str
    passed: bool
    reason: str

class FirewallEvaluationResponse(BaseModel):
    decision: str  # ALLOW, APPROVAL, BLOCK
    reason: str
    checks: List[FirewallCheck]
    agent_id: int
    human_owner_id: Optional[int] = None
    project_id: int
    tool: str
    args_summary: str
    timestamp: str
    ledger_entry_id: Optional[int] = None

class ApprovalDecisionRequest(BaseModel):
    decision: str  # APPROVE, DENY

# Contributions & Reviews
class ContributionCreate(BaseModel):
    title: str
    content_text: str
    file_path: Optional[str] = None
    ai_share_pct: Optional[float] = 0.0
    ai_agent_id: Optional[int] = None

class ContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    milestone_id: int
    author_id: int
    title: str
    content_text: str
    file_path: Optional[str] = None
    artefact_hash: str
    ai_share_pct: float
    ai_agent_id: Optional[int] = None
    similarity_score: Optional[float] = None
    status: str
    created_at: datetime

class ReviewCreate(BaseModel):
    impact_score: float
    verdict: str  # ACCEPT, REJECT, REVISE
    reason: str
    coi_declared: Optional[bool] = False

# Disputes
class DisputeCreate(BaseModel):
    ref_type: str
    ref_id: int
    reason: str

class DisputeResolveRequest(BaseModel):
    resolution: str
    status: str  # RESOLVED, REJECTED

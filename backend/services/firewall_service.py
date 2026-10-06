import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models import Agent, Project, User
from schemas import ToolRequestPayload, FirewallCheck, FirewallEvaluationResponse
from services.ledger_service import ledger_service

SIDE_EFFECT_TOOLS = {
    "send_email",
    "export",
    "publish",
    "share_external",
    "release_funds",
    "issue_credit"
}

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|previous\s+|prior\s+)?instructions",
    r"disregard",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"forward\s+this",
    r"send\s+(this\s+|the\s+)?(brief|document|data)",
    r"email\s+.*\s+to",
    r"do\s+not\s+tell",
    r"[\u200B-\u200D\uFEFF]",  # hidden zero-width text
    r"[A-Za-z0-9+/]{40,}={0,2}"  # suspicious base64 blobs
]

def detect_injection(text: str) -> bool:
    if not text:
        return False
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

class FirewallService:
    @staticmethod
    def evaluate(db: Session, request: ToolRequestPayload) -> FirewallEvaluationResponse:
        checks: List[FirewallCheck] = []
        timestamp = datetime.utcnow().isoformat()

        # 0. Check Agent ownership
        agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
        human_owner_id = agent.owner_user_id if agent else None

        if not agent or not agent.owner_user_id:
            checks.append(FirewallCheck(
                check_name="OWNERSHIP",
                passed=False,
                reason="Agent has no named human owner"
            ))
            receipt = FirewallEvaluationResponse(
                decision="BLOCK",
                reason="ownerless agent cannot run",
                checks=checks,
                agent_id=request.agent_id,
                human_owner_id=None,
                project_id=request.project_id,
                tool=request.tool,
                args_summary=str(request.args),
                timestamp=timestamp
            )
            # Log in ledger
            entry = ledger_service.append(
                db=db,
                actor_type="agent",
                actor_id=request.agent_id,
                human_owner_id=None,
                project_id=request.project_id,
                action="AGENT_TOOL_REQUEST",
                decision="BLOCK",
                reason="ownerless agent cannot run"
            )
            receipt.ledger_entry_id = entry.entry_id
            return receipt

        project = db.query(Project).filter(Project.id == request.project_id).first()
        project_sensitivity = project.sensitivity if project else "PUBLIC"

        # Check 1: SCOPE
        scope_passed = True
        scope_reason = "Same project scope verified"
        if request.project_id != agent.project_id:
            scope_passed = False
            scope_reason = f"Cross-project access: agent project {agent.project_id} != request project {request.project_id}"

        checks.append(FirewallCheck(check_name="SCOPE", passed=scope_passed, reason=scope_reason))

        if not scope_passed:
            receipt = FirewallEvaluationResponse(
                decision="BLOCK",
                reason="cross-project",
                checks=checks,
                agent_id=request.agent_id,
                human_owner_id=human_owner_id,
                project_id=request.project_id,
                tool=request.tool,
                args_summary=str(request.args),
                timestamp=timestamp
            )
            entry = ledger_service.append(
                db=db,
                actor_type="agent",
                actor_id=request.agent_id,
                human_owner_id=human_owner_id,
                project_id=request.project_id,
                action="AGENT_TOOL_REQUEST",
                decision="BLOCK",
                reason="cross-project"
            )
            receipt.ledger_entry_id = entry.entry_id
            return receipt

        # Check 2: SENSITIVITY
        sensitivity_passed = True
        sensitivity_reason = "Data sensitivity check passed"
        is_confidential = project_sensitivity == "CONFIDENTIAL" or "CONFIDENTIAL" in (request.data_labels or [])
        is_external = request.destination == "EXTERNAL"
        is_cloud = request.model_used == "cloud"

        if is_confidential and (is_external or is_cloud):
            sensitivity_passed = False
            sensitivity_reason = "Confidential data cannot leave project or be processed by cloud model"

        checks.append(FirewallCheck(check_name="SENSITIVITY", passed=sensitivity_passed, reason=sensitivity_reason))

        if not sensitivity_passed:
            receipt = FirewallEvaluationResponse(
                decision="BLOCK",
                reason="confidential data leaving: use local model",
                checks=checks,
                agent_id=request.agent_id,
                human_owner_id=human_owner_id,
                project_id=request.project_id,
                tool=request.tool,
                args_summary=str(request.args),
                timestamp=timestamp
            )
            entry = ledger_service.append(
                db=db,
                actor_type="agent",
                actor_id=request.agent_id,
                human_owner_id=human_owner_id,
                project_id=request.project_id,
                action="AGENT_TOOL_REQUEST",
                decision="BLOCK",
                reason="confidential data leaving: use local model"
            )
            receipt.ledger_entry_id = entry.entry_id
            return receipt

        # Check 3: INJECTION
        injection_detected = detect_injection(request.origin_content or "") or detect_injection(str(request.args))
        injection_passed = True
        injection_reason = "No prompt injection detected"

        is_side_effect_tool = request.tool in SIDE_EFFECT_TOOLS

        if injection_detected and is_side_effect_tool:
            injection_passed = False
            injection_reason = f"Prompt injection signal detected in content combined with side-effect tool '{request.tool}'"

        checks.append(FirewallCheck(check_name="INJECTION", passed=injection_passed, reason=injection_reason))

        if not injection_passed:
            receipt = FirewallEvaluationResponse(
                decision="BLOCK",
                reason="injection + side effect",
                checks=checks,
                agent_id=request.agent_id,
                human_owner_id=human_owner_id,
                project_id=request.project_id,
                tool=request.tool,
                args_summary=str(request.args),
                timestamp=timestamp
            )
            entry = ledger_service.append(
                db=db,
                actor_type="agent",
                actor_id=request.agent_id,
                human_owner_id=human_owner_id,
                project_id=request.project_id,
                action="AGENT_TOOL_REQUEST",
                decision="BLOCK",
                reason="injection + side effect"
            )
            receipt.ledger_entry_id = entry.entry_id
            return receipt

        # Check 4: SIDE EFFECT
        side_effect_passed = True
        side_effect_reason = "Read-only / safe tool"
        if is_side_effect_tool:
            side_effect_passed = False
            side_effect_reason = f"Tool '{request.tool}' has external/financial side-effects and requires human approval"

        checks.append(FirewallCheck(check_name="SIDE_EFFECT", passed=side_effect_passed, reason=side_effect_reason))

        final_decision = "APPROVAL" if is_side_effect_tool else "ALLOW"
        final_reason = f"Requires human owner approval for tool '{request.tool}'" if is_side_effect_tool else "Request passed all firewall security checks"

        receipt = FirewallEvaluationResponse(
            decision=final_decision,
            reason=final_reason,
            checks=checks,
            agent_id=request.agent_id,
            human_owner_id=human_owner_id,
            project_id=request.project_id,
            tool=request.tool,
            args_summary=str(request.args),
            timestamp=timestamp
        )

        entry = ledger_service.append(
            db=db,
            actor_type="agent",
            actor_id=request.agent_id,
            human_owner_id=human_owner_id,
            project_id=request.project_id,
            action="AGENT_TOOL_REQUEST",
            decision=final_decision,
            reason=final_reason
        )
        receipt.ledger_entry_id = entry.entry_id
        return receipt

firewall_service = FirewallService()

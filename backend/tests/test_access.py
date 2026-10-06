import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_dir = os.path.join(os.path.dirname(__file__), "..")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from main import app
from db import Base, setup_ledger_triggers, get_db
from models import LedgerEntry, Project
from security import create_access_token

seed_dir = os.path.join(backend_dir, "..", "seed")
if seed_dir not in sys.path:
    sys.path.append(seed_dir)

import seed

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    from db import engine, SessionLocal
    Base.metadata.create_all(bind=engine)
    setup_ledger_triggers()
    db = SessionLocal()
    seed.run_seed(db)
    db.close()

def test_non_member_confidential_brief_403():
    # Student Priya (id=4) has not accepted charter initially
    token = create_access_token({"sub": "4", "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/projects/1", headers=headers)
    assert response.status_code == 403

    from db import SessionLocal
    db = SessionLocal()
    entry = db.query(LedgerEntry).filter(
        LedgerEntry.action == "BRIEF_ACCESS_DENIED",
        LedgerEntry.actor_id == 4
    ).first()
    assert entry is not None
    assert entry.decision == "BLOCK"
    db.close()

def test_unpaid_project_no_currency_symbols():
    from db import SessionLocal
    db = SessionLocal()
    unpaid_project = db.query(Project).filter(Project.engagement_model == "KNOWLEDGE").first()
    assert unpaid_project is not None
    
    summary_text = unpaid_project.public_summary or ""
    assert "Rs" not in summary_text
    assert "₹" not in summary_text
    db.close()

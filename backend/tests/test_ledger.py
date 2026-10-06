import pytest
import sys
import os
import tempfile
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

backend_dir = os.path.join(os.path.dirname(__file__), "..")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db import Base
from models import LedgerEntry
from services.ledger_service import ledger_service

@pytest.fixture
def test_db():
    db_fd, db_path = tempfile.mkstemp()
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
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

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    yield db, engine
    db.close()
    engine.dispose()
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except Exception:
        pass

def test_ledger_append_and_verify(test_db):
    db, engine = test_db
    e1 = ledger_service.append(db, actor_type="human", actor_id=1, action="PROJECT_POSTED", reason="First post")
    e2 = ledger_service.append(db, actor_type="human", actor_id=2, action="CHARTER_ACCEPTED", reason="Accepted")

    res = ledger_service.verify(db)
    assert res["ok"] is True
    assert res["count"] == 2
    assert res["head_hash"] == e2.current_hash

def test_ledger_trigger_blocks_update(test_db):
    db, engine = test_db
    e1 = ledger_service.append(db, actor_type="human", actor_id=1, action="PROJECT_POSTED")
    
    with pytest.raises(Exception) as exc_info:
        with engine.connect() as conn:
            conn.execute(text("UPDATE ledger_entries SET action = 'TAMPERED' WHERE entry_id = 1;"))
            conn.commit()
    assert "append-only" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower()

def test_ledger_tamper_detection(test_db):
    db, engine = test_db
    e1 = ledger_service.append(db, actor_type="human", actor_id=1, action="PROJECT_POSTED")
    e2 = ledger_service.append(db, actor_type="human", actor_id=2, action="CHARTER_ACCEPTED")

    # Bypass trigger to simulate tamper
    with engine.connect() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS prevent_ledger_update;"))
        conn.execute(text("UPDATE ledger_entries SET current_hash = 'corrupted_hash' WHERE entry_id = 1;"))
        conn.commit()

    res = ledger_service.verify(db)
    assert res["ok"] is False
    assert res["error"] == "HASH_MISMATCH"
    assert res["entry_id"] == 1

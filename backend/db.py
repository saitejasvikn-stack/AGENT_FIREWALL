from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def setup_ledger_triggers():
    """Sets up SQLite triggers to enforce append-only ledger rules."""
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from db import Base, engine, setup_ledger_triggers, SessionLocal
from config import settings

from routers import (
    auth, projects, charters, milestones, matching,
    workspace, firewall, ledger, escrow, rewards,
    reviews, disputes, admin, demo
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    setup_ledger_triggers()

    db = SessionLocal()
    try:
        from models import User
        if db.query(User).count() == 0:
            import sys
            seed_dir = os.path.join(os.path.dirname(__file__), "..", "seed")
            if seed_dir not in sys.path:
                sys.path.append(seed_dir)
            try:
                import seed
                seed.run_seed(db)
            except Exception as e:
                print(f"Auto-seed note: {e}")
    finally:
        db.close()

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Agent Firewall Hackathon Prototype — AI can act. AI cannot decide what it is allowed to do.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(charters.router)
app.include_router(milestones.router)
app.include_router(matching.router)
app.include_router(workspace.router)
app.include_router(firewall.router)
app.include_router(ledger.router)
app.include_router(escrow.router)
app.include_router(rewards.router)
app.include_router(reviews.router)
app.include_router(disputes.router)
app.include_router(admin.router)
app.include_router(demo.router)

# Static files for full frontend UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "principle": "AI can act. AI cannot decide what it is allowed to do."
    }

import os

class Settings:
    PROJECT_NAME: str = "Agent Firewall"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "demo-agent-firewall-secret-key-2026-super-secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agent_firewall.db")
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "1") == "1"
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-flash")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")

settings = Settings()

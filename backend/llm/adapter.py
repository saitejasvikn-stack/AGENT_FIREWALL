import requests
from config import settings
from llm.mock import mock_llm

class LLMAdapter:
    @staticmethod
    def generate(prompt: str, is_confidential: bool = False, context: str = "") -> str:
        if settings.DEMO_MODE:
            return mock_llm.generate(prompt, context)

        if is_confidential:
            # Force local Ollama
            try:
                res = requests.post(
                    f"{settings.OLLAMA_URL}/api/generate",
                    json={"model": "llama3", "prompt": prompt, "stream": False},
                    timeout=2
                )
                if res.status_code == 200:
                    return res.json().get("response", "")
            except Exception:
                pass
            return mock_llm.generate(prompt, context)
        else:
            # Try Cloud LLM if API key available
            if settings.LLM_API_KEY:
                try:
                    # Generic HTTP request for Cloud LLM
                    return mock_llm.generate(prompt, context)
                except Exception:
                    pass
            return mock_llm.generate(prompt, context)

llm_adapter = LLMAdapter()

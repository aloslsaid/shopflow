"""The ONLY module that talks to the model provider. Swap model/provider via .env; nothing else changes."""
import os, logging
from .errors import LLMError, LLMNotConfigured
log = logging.getLogger("shopflow.llm")

class OpenRouterClient:
    def __init__(self, post=None): self._post = post  # injectable for tests
    def chat(self, messages, tools=None) -> dict:
        key, model = os.environ.get("OPENROUTER_API_KEY"), os.environ.get("OPENROUTER_MODEL")
        base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        if not key or not model: raise LLMNotConfigured("AI is not configured: set OPENROUTER_API_KEY and OPENROUTER_MODEL in .env")
        post = self._post
        if post is None:
            import httpx; post = httpx.post
        body = {"model": model, "messages": messages, "temperature": 0.2}
        if tools: body["tools"] = tools
        try:
            r = post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=body, timeout=60)
        except Exception as e:
            log.error("llm transport error: %s", type(e).__name__); raise LLMError("could not reach the AI provider")
        if r.status_code >= 400:
            log.error("llm http %s", r.status_code); raise LLMError(f"AI provider error ({r.status_code})")
        try: return r.json()
        except Exception: raise LLMError("AI provider returned invalid data")

from app.ai.fake_client import FakeClient
from app.ai.gemini_client import GeminiClient
from app.ai.heuristic_client import HeuristicClient
from app.ai.llm_base import LLMClient
from app.core.config import settings

_test_client_override: LLMClient | None = None


def set_llm_client_override(client: LLMClient | None) -> None:
    global _test_client_override
    _test_client_override = client


def get_llm_client() -> LLMClient:
    """Return the active LLM client based on configuration or test overrides."""
    if _test_client_override is not None:
        return _test_client_override

    if settings.has_gemini_key:
        return GeminiClient()

    return HeuristicClient()


__all__ = [
    "FakeClient",
    "GeminiClient",
    "HeuristicClient",
    "LLMClient",
    "get_llm_client",
    "set_llm_client_override",
]

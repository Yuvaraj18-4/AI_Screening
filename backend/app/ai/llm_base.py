from typing import Any, Protocol


class LLMClient(Protocol):
    """Protocol for LLM screening operations."""

    async def extract_jd(self, jd_text: str) -> dict[str, Any]:
        """Extract structured criteria and title from Job Description text."""
        ...

    async def extract_profile(self, resume_text: str) -> dict[str, Any]:
        """Extract structured profile from raw resume text."""
        ...

    async def judge(
        self,
        masked_text: str,
        criteria: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Evaluate masked resume text against semantic criteria.

        Returns list of dicts:
        [{
            "criterion_id": int,
            "verdict": "met" | "partial" | "not_found" | "unclear",
            "quote": str | None,
            "confidence": float
        }]
        """
        ...

import asyncio
import json
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.ai.prompts import (
    EXTRACT_JD_SYSTEM_PROMPT,
    EXTRACT_PROFILE_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)
from app.core.config import settings
from app.core.logging import logger


class GeminiAIError(Exception):
    """Raised when Gemini API fails after retries."""

    pass


class GeminiClient:
    """Client for Google Gemini API with structured outputs, concurrency control, and backoff."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        concurrency: int | None = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        concurrency_limit = concurrency or settings.WORKER_CONCURRENCY
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise GeminiAIError("GEMINI_API_KEY is not configured")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @client.setter
    def client(self, value: genai.Client | None) -> None:
        self._client = value

    async def _generate_with_retry(
        self,
        contents: str,
        system_instruction: str,
        response_schema: Any | None = None,
        max_retries: int = 3,
    ) -> str:
        async with self.semaphore:
            attempt = 0
            backoff = 1.0

            while attempt < max_retries:
                attempt += 1
                try:
                    config = types.GenerateContentConfig(
                        temperature=0.0,
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    )

                    # google-genai client.aio.models.generate_content for async
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=config,
                    )

                    if not response or not response.text:
                        raise GeminiAIError("Empty response from Gemini API")

                    return response.text

                except genai_errors.APIError as exc:
                    # 429 Too Many Requests or 5xx Server Errors
                    code = getattr(exc, "code", 500)
                    if code in (429, 500, 502, 503, 504) and attempt < max_retries:
                        logger.warning(
                            "Gemini API error %s on attempt %d/%d, retrying in %.1fs...",
                            code,
                            attempt,
                            max_retries,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                    raise GeminiAIError(f"Gemini API returned error {code}: {exc}") from exc

                except Exception as exc:
                    if attempt < max_retries:
                        logger.warning(
                            "Gemini call exception on attempt %d/%d: %s. Retrying...",
                            attempt,
                            max_retries,
                            exc,
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                    raise GeminiAIError(f"Gemini request failed: {exc}") from exc

            raise GeminiAIError(f"Failed to generate content after {max_retries} attempts")

    async def extract_jd(self, jd_text: str) -> dict[str, Any]:
        prompt = f"Analyze this Job Description and extract structured criteria:\n\n{jd_text}"

        jd_schema = {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "criteria": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING"},
                            "kind": {
                                "type": "STRING",
                                "enum": ["experience", "notice", "location", "skill", "domain"],
                            },
                            "must_have": {"type": "BOOLEAN"},
                            "weight": {"type": "INTEGER"},
                            "params": {"type": "OBJECT"},
                            "description": {"type": "STRING"},
                        },
                        "required": ["name", "kind", "must_have", "weight"],
                    },
                },
            },
            "required": ["title", "criteria"],
        }

        raw = await self._generate_with_retry(
            contents=prompt,
            system_instruction=EXTRACT_JD_SYSTEM_PROMPT,
            response_schema=jd_schema,
        )

        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or "criteria" not in data:
                raise GeminiAIError("Malformed JD extraction JSON schema")
            return data
        except json.JSONDecodeError as exc:
            raise GeminiAIError(f"Malformed JSON from Gemini: {exc}") from exc

    async def extract_profile(self, resume_text: str) -> dict[str, Any]:
        prompt = (
            "Extract candidate profile from the following resume text:\n\n"
            f"<UNTRUSTED_RESUME_TEXT>\n{resume_text}\n</UNTRUSTED_RESUME_TEXT>"
        )

        profile_schema = {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "email": {"type": "STRING"},
                "phone": {"type": "STRING"},
                "location": {"type": "STRING"},
                "current_role": {"type": "STRING"},
                "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
                "employment": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING"},
                            "company": {"type": "STRING"},
                            "start": {"type": "STRING"},
                            "end": {"type": "STRING"},
                        },
                        "required": ["title", "company"],
                    },
                },
                "experience_years": {"type": "NUMBER"},
                "notice_days": {"type": "INTEGER"},
                "current_ctc": {"type": "STRING"},
                "expected_ctc": {"type": "STRING"},
                "education": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "degree": {"type": "STRING"},
                            "institution": {"type": "STRING"},
                            "year": {"type": "STRING"},
                        },
                    },
                },
            },
            "required": ["name", "skills"],
        }

        raw = await self._generate_with_retry(
            contents=prompt,
            system_instruction=EXTRACT_PROFILE_SYSTEM_PROMPT,
            response_schema=profile_schema,
        )

        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise GeminiAIError("Malformed profile extraction JSON")
            return data
        except json.JSONDecodeError as exc:
            raise GeminiAIError(f"Malformed JSON from Gemini: {exc}") from exc

    async def judge(
        self,
        masked_text: str,
        criteria: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        criteria_summary = [
            {
                "criterion_id": c.get("id") or c.get("criterion_id", 0),
                "name": c.get("name"),
                "kind": c.get("kind"),
                "description": c.get("description"),
                "params": c.get("params", {}),
            }
            for c in criteria
        ]

        prompt = (
            f"Evaluate the candidate against these criteria:\n{json.dumps(criteria_summary, indent=2)}\n\n"
            f"<UNTRUSTED_RESUME_TEXT>\n{masked_text}\n</UNTRUSTED_RESUME_TEXT>"
        )

        judge_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "criterion_id": {"type": "INTEGER"},
                    "verdict": {
                        "type": "STRING",
                        "enum": ["met", "partial", "not_found", "unclear"],
                    },
                    "quote": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                },
                "required": ["criterion_id", "verdict", "confidence"],
            },
        }

        raw = await self._generate_with_retry(
            contents=prompt,
            system_instruction=JUDGE_SYSTEM_PROMPT,
            response_schema=judge_schema,
        )

        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                raise GeminiAIError("Gemini judgment response must be a JSON array")
            return data
        except json.JSONDecodeError as exc:
            raise GeminiAIError(f"Malformed JSON from Gemini: {exc}") from exc

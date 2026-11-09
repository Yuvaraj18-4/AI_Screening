import contextlib
import re
from typing import Any

from app.ai import get_llm_client
from app.parsing.experience import compute_experience_years
from app.parsing.notice import normalise_notice_period


async def parse_candidate_profile(raw_text: str) -> dict[str, Any]:
    llm = get_llm_client()
    extracted = await llm.extract_profile(raw_text)

    # Regex email fallback
    email = extracted.get("email") or ""
    if not email or "@" not in email:
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_text)
        if email_match:
            email = email_match.group(0).lower().strip()

    # Regex phone fallback
    phone = extracted.get("phone") or ""
    if not phone:
        phone_match = re.search(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text
        )
        if phone_match:
            phone = phone_match.group(0).strip()

    # Compute experience years
    employment = extracted.get("employment") or []
    exp_years, parse_quality = compute_experience_years(employment, raw_text)
    if exp_years == 0.0 and extracted.get("experience_years"):
        with contextlib.suppress(ValueError, TypeError):
            exp_years = float(extracted["experience_years"])

    # Normalise notice period
    notice_raw = extracted.get("notice_days")
    notice_days = normalise_notice_period(notice_raw, raw_text)

    # Name cleanup
    name = (extracted.get("name") or "").strip()
    if not name:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        name = lines[0] if lines else "Candidate"

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "location": extracted.get("location") or "",
        "current_role": extracted.get("current_role") or "",
        "skills": extracted.get("skills") or [],
        "employment": employment,
        "experience_years": exp_years,
        "notice_days": notice_days,
        "current_ctc": str(extracted.get("current_ctc") or ""),
        "expected_ctc": str(extracted.get("expected_ctc") or ""),
        "education": extracted.get("education") or [],
        "parse_quality": parse_quality,
    }

import hashlib
import re
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CVFile


class DedupMatch(NamedTuple):
    is_duplicate: bool
    duplicate_of_id: int | None
    match_type: str | None  # "exact" | "near"
    similarity: float


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def tokenize_text(text: str) -> set[str]:
    # Extract lowercased alphanumeric words of length >= 3
    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
    return set(words)


def compute_jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    if union == 0:
        return 0.0
    return intersection / union


async def find_duplicate_candidate(
    db: AsyncSession,
    file_sha256: str,
    extracted_text: str,
    candidate_id_to_exclude: int | None = None,
) -> DedupMatch:
    # 1. Exact SHA-256 match in cv_files
    query_sha = select(CVFile).where(CVFile.sha256 == file_sha256)
    if candidate_id_to_exclude:
        query_sha = query_sha.where(CVFile.candidate_id != candidate_id_to_exclude)

    res_sha = await db.execute(query_sha)
    exact_match = res_sha.scalars().first()
    if exact_match:
        return DedupMatch(
            is_duplicate=True,
            duplicate_of_id=exact_match.candidate_id,
            match_type="exact",
            similarity=1.0,
        )

    # 2. Near-duplicate match: Jaccard similarity >= 0.85 on token sets
    current_tokens = tokenize_text(extracted_text)
    if len(current_tokens) < 10:
        return DedupMatch(is_duplicate=False, duplicate_of_id=None, match_type=None, similarity=0.0)

    # Fetch recent active CV files
    cv_query = select(CVFile.candidate_id, CVFile.text).where(CVFile.text != "")
    if candidate_id_to_exclude:
        cv_query = cv_query.where(CVFile.candidate_id != candidate_id_to_exclude)

    cv_res = await db.execute(cv_query)
    for other_cand_id, other_text in cv_res.all():
        other_tokens = tokenize_text(other_text)
        sim = compute_jaccard_similarity(current_tokens, other_tokens)
        if sim >= 0.85:
            return DedupMatch(
                is_duplicate=True,
                duplicate_of_id=other_cand_id,
                match_type="near",
                similarity=round(sim, 3),
            )

    return DedupMatch(is_duplicate=False, duplicate_of_id=None, match_type=None, similarity=0.0)

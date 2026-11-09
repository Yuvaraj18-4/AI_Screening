import hashlib
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import get_llm_client
from app.ai.prompts import PROMPT_VERSION
from app.ai.verifier import verify_quote
from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    Application,
    Candidate,
    Criterion,
    CriterionResult,
    CVFile,
    Score,
    Scorecard,
)


def compute_cache_key(
    masked_text: str,
    scorecard_version: int,
    prompt_version: str,
    model: str,
) -> str:
    raw = f"{masked_text}###{scorecard_version}###{prompt_version}###{model}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def calculate_weighted_score(
    criteria: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    """Calculates weighted total score and identifies must-have gaps.

    Formula: sum(weight * value) / sum(weight) * 100
    Gaps: any criterion where must_have is True and value < 1.0
    """
    total_weighted_points = 0.0
    total_weights = 0.0
    gaps: list[str] = []

    for crit, res in zip(criteria, results, strict=False):
        weight = float(crit.get("weight", 1))
        val = float(res.get("value", 0.0))
        must_have = bool(crit.get("must_have", False))
        name = crit.get("name", "Criterion")

        total_weights += weight
        total_weighted_points += weight * val

        if must_have and val < 1.0:
            gaps.append(name)

    final_total = (
        round((total_weighted_points / total_weights) * 100, 1) if total_weights > 0 else 0.0
    )
    return final_total, gaps


def evaluate_deterministic_criterion(
    criterion: Criterion,
    candidate: Candidate,
) -> dict[str, Any]:
    """Evaluate experience, notice, or location criteria purely in code."""
    kind = criterion.kind
    params = criterion.params or {}

    if kind == "experience":
        min_years = float(params.get("min", 0.0))
        max_years = float(params.get("max", 100.0))
        actual = candidate.experience_years

        if actual >= min_years and actual <= max_years + 3.0:
            verdict = "met"
            val = 1.0
        elif actual >= max_years + 3.0:
            verdict = "met"  # Overqualified still meets requirement
            val = 1.0
        elif actual >= max_years or actual >= max(0.0, min_years - 1.0):
            verdict = "partial"
            val = 0.5
        else:
            verdict = "not_found"
            val = 0.0

        quote = f"Total experience: {actual} years (Required: {min_years}-{max_years} yrs)"
        return {
            "verdict": verdict,
            "value": val,
            "quote": quote,
            "quote_verified": True,
            "confidence": 1.0,
            "source": "code",
        }

    elif kind == "notice":
        max_days = int(params.get("max_days", 60))
        actual = candidate.notice_days

        if actual <= max_days:
            verdict = "met"
            val = 1.0
        elif actual <= max_days + 15:
            verdict = "partial"
            val = 0.5
        else:
            verdict = "not_found"
            val = 0.0

        quote = f"Notice period: {actual} days (Acceptable: <= {max_days} days)"
        return {
            "verdict": verdict,
            "value": val,
            "quote": quote,
            "quote_verified": True,
            "confidence": 1.0,
            "source": "code",
        }

    elif kind == "location":
        target = str(params.get("city") or params.get("target") or criterion.name or "").strip().lower()
        cand_loc = (candidate.location or "").lower()

        # Equivalence matching (e.g. Noida / Gurgaon in Delhi/NCR)
        ncr_keywords = ["ncr", "delhi", "noida", "gurgaon"]
        if any(k in target for k in ncr_keywords):
            is_match = any(k in cand_loc for k in ncr_keywords)
        else:
            is_match = bool(target and target in cand_loc)

        verdict = "met" if is_match else "not_found"
        val = 1.0 if is_match else 0.0
        quote = f"Candidate location: {candidate.location or 'Not specified'}"

        return {
            "verdict": verdict,
            "value": val,
            "quote": quote,
            "quote_verified": True,
            "confidence": 0.95,
            "source": "code",
        }

    return {
        "verdict": "not_found",
        "value": 0.0,
        "quote": None,
        "quote_verified": False,
        "confidence": 0.5,
        "source": "code",
    }


async def evaluate_and_score_application(
    db: AsyncSession,
    application_id: int,
    force_rescore: bool = False,
) -> Score:
    app_obj = await db.get(Application, application_id)
    if not app_obj:
        raise ValueError(f"Application {application_id} not found")

    candidate = await db.get(Candidate, app_obj.candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {app_obj.candidate_id} not found")

    # Get latest active CV file
    cv_query = select(CVFile).where(CVFile.candidate_id == candidate.id).order_by(CVFile.id.desc())
    cv_res = await db.execute(cv_query)
    cv_file = cv_res.scalars().first()
    masked_text = cv_file.masked_text if cv_file else ""

    # Get active scorecard for requisition
    sc_query = (
        select(Scorecard)
        .options(selectinload(Scorecard.criteria))
        .where(
            Scorecard.requisition_id == app_obj.requisition_id,
            Scorecard.is_active == True,  # noqa: E712
        )
    )
    sc = (await db.execute(sc_query)).scalar_one_or_none()
    if not sc or not sc.criteria:
        logger.warning(
            "No active scorecard with criteria for requisition %d", app_obj.requisition_id
        )
        # Return pending dummy score
        score = Score(
            application_id=app_obj.id,
            scorecard_version=0,
            total=0.0,
            confidence="low",
            status="pending",
            cache_key=f"pending_{app_obj.id}",
            model="none",
            prompt_version=PROMPT_VERSION,
            scoring_mode="heuristic",
        )
        db.add(score)
        await db.commit()
        return score

    model_name = settings.GEMINI_MODEL if settings.has_gemini_key else "heuristic-keywords"
    cache_key = compute_cache_key(
        masked_text=masked_text,
        scorecard_version=sc.version,
        prompt_version=PROMPT_VERSION,
        model=model_name,
    )

    # 1. Check existing cached score
    if not force_rescore:
        existing_score_q = (
            select(Score)
            .options(selectinload(Score.criterion_results))
            .where(Score.application_id == app_obj.id, Score.cache_key == cache_key)
        )
        existing_score = (await db.execute(existing_score_q)).scalar_one_or_none()
        if existing_score:
            logger.info("Cache hit for application %d (cache_key: %s)", app_obj.id, cache_key[:12])
            return existing_score

    # Remove any prior scores for this application to keep clean latest
    await db.execute(delete(Score).where(Score.application_id == app_obj.id))

    deterministic_results: dict[int, dict[str, Any]] = {}
    semantic_criteria: list[dict[str, Any]] = []

    for crit in sc.criteria:
        if crit.kind in ("experience", "notice", "location"):
            res = evaluate_deterministic_criterion(crit, candidate)
            deterministic_results[crit.id] = res
        else:
            semantic_criteria.append(
                {
                    "id": crit.id,
                    "criterion_id": crit.id,
                    "name": crit.name,
                    "kind": crit.kind,
                    "description": crit.description,
                    "params": crit.params,
                }
            )

    # Evaluate semantic criteria via LLM/Heuristic with error protection
    semantic_evaluations: list[dict[str, Any]] = []
    scoring_mode = "llm" if settings.has_gemini_key else "heuristic"
    ai_failed = False

    if semantic_criteria:
        try:
            llm = get_llm_client()
            semantic_evaluations = await llm.judge(masked_text, semantic_criteria)
        except Exception as exc:
            logger.error("AI judgment failed for application %d: %s", app_obj.id, exc)
            ai_failed = True

    # Build Score record
    if ai_failed:
        score = Score(
            application_id=app_obj.id,
            scorecard_version=sc.version,
            total=0.0,
            confidence="low",
            status="ai_failed",
            cache_key=cache_key,
            model=model_name,
            prompt_version=PROMPT_VERSION,
            scoring_mode=scoring_mode,
        )
        db.add(score)
        await db.commit()
        await db.refresh(score)
        return score

    # Map semantic evaluations by criterion_id
    semantic_by_id = {}
    for sem in semantic_evaluations:
        c_id = sem.get("criterion_id") or sem.get("id")
        if c_id is not None:
            semantic_by_id[int(c_id)] = sem

    all_criterion_results = []
    total_weighted_points = 0.0
    total_weights = 0
    unverified_count = 0
    unclear_count = 0

    for crit in sc.criteria:
        total_weights += crit.weight

        if crit.id in deterministic_results:
            det = deterministic_results[crit.id]
            verdict = det["verdict"]
            val = det["value"]
            quote = det["quote"]
            quote_verified = det["quote_verified"]
            conf = det["confidence"]
            src = det["source"]
        else:
            sem = semantic_by_id.get(crit.id, {})
            raw_verdict = sem.get("verdict", "not_found")
            raw_quote = sem.get("quote")
            conf = float(sem.get("confidence", 0.8))
            src = "llm" if settings.has_gemini_key else "heuristic"

            # Quote verification on CV text
            if raw_verdict in ("met", "partial") and raw_quote:
                is_verified = verify_quote(raw_quote, masked_text)
                if is_verified:
                    verdict = raw_verdict
                    val = 1.0 if raw_verdict == "met" else 0.5
                    quote = raw_quote
                    quote_verified = True
                else:
                    # Hallucination detected
                    verdict = "unverified"
                    val = 0.0
                    quote = raw_quote
                    quote_verified = False
                    unverified_count += 1
            else:
                verdict = (
                    raw_verdict
                    if raw_verdict in ("met", "partial", "not_found", "unclear")
                    else "not_found"
                )
                val = 1.0 if verdict == "met" else (0.5 if verdict == "partial" else 0.0)
                quote = raw_quote
                quote_verified = False
                if verdict == "unclear":
                    unclear_count += 1

        total_weighted_points += crit.weight * val

        crit_result = CriterionResult(
            criterion_id=crit.id,
            verdict=verdict,
            value=val,
            quote=quote,
            quote_verified=quote_verified,
            confidence=conf,
            source=src,
        )
        all_criterion_results.append(crit_result)

    # Score calculation
    final_total = (
        round((total_weighted_points / total_weights) * 100, 1) if total_weights > 0 else 0.0
    )

    # Confidence calculation:
    # low if parse_quality low, or any unverified quote, or >= 30% criteria unclear;
    # medium for one flag; else high.
    flags = 0
    if candidate.parse_quality < 0.6:
        flags += 1
    if unverified_count > 0:
        flags += 1
    if total_weights > 0 and (unclear_count / len(sc.criteria)) >= 0.3:
        flags += 1

    if flags >= 2 or unverified_count > 0:
        confidence = "low"
    elif flags == 1:
        confidence = "medium"
    else:
        confidence = "high"

    score = Score(
        application_id=app_obj.id,
        scorecard_version=sc.version,
        total=final_total,
        confidence=confidence,
        status="scored",
        cache_key=cache_key,
        model=model_name,
        prompt_version=PROMPT_VERSION,
        scoring_mode=scoring_mode,
        criterion_results=all_criterion_results,
    )
    db.add(score)

    # If application was in "sourced" stage, advance to "screened"
    if app_obj.stage == "sourced":
        app_obj.stage = "screened"

    await db.commit()
    res = await db.execute(
        select(Score).options(selectinload(Score.criterion_results)).where(Score.id == score.id)
    )
    return res.scalar_one()

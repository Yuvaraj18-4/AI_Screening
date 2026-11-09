from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.masking import mask_personal_data
from app.db.models import Application, Candidate, CVFile, Scorecard
from app.parsing.dedup import find_duplicate_candidate
from app.parsing.extract_text import extract_cv_text
from app.parsing.profile import parse_candidate_profile


async def handle_parse_cv(db: AsyncSession, payload: dict[str, Any], batch_id: int | None) -> None:
    cv_file_id = payload["cv_file_id"]
    requisition_id = payload["requisition_id"]
    candidate_id = payload["candidate_id"]

    cv_file = await db.get(CVFile, cv_file_id)
    if not cv_file:
        raise ValueError(f"CVFile {cv_file_id} not found")

    candidate = await db.get(Candidate, candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    # 1. Extract text from PDF / DOCX
    ext_result = extract_cv_text(cv_file.filename, cv_file.content)
    cv_file.text = ext_result.text
    cv_file.parse_status = ext_result.parse_status
    cv_file.parse_error = ext_result.parse_error

    if ext_result.parse_status == "failed":
        await db.commit()
        return

    # 2. Check duplicates (exact SHA256 or near-duplicate)
    dedup = await find_duplicate_candidate(
        db,
        file_sha256=cv_file.sha256,
        extracted_text=ext_result.text,
        candidate_id_to_exclude=candidate_id,
    )
    if dedup.is_duplicate and dedup.duplicate_of_id:
        candidate.duplicate_of_id = dedup.duplicate_of_id
        if cv_file.parse_status == "ok":
            cv_file.parse_status = "needs_review"
            cv_file.parse_error = (
                f"Duplicate detected ({dedup.match_type} match, sim {dedup.similarity})"
            )

    # 3. Extract candidate profile
    profile = await parse_candidate_profile(ext_result.text)
    candidate.name = profile["name"]
    candidate.email = profile["email"]
    candidate.phone = profile["phone"]
    candidate.location = profile["location"]
    candidate.current_role = profile["current_role"]
    candidate.skills = profile["skills"]
    candidate.employment = profile["employment"]
    candidate.experience_years = profile["experience_years"]
    candidate.notice_days = profile["notice_days"]
    candidate.current_ctc = profile["current_ctc"]
    candidate.expected_ctc = profile["expected_ctc"]
    candidate.education = profile["education"]
    candidate.parse_quality = 0.4 if ext_result.is_scan else profile["parse_quality"]

    # 4. Build masked text
    masked_text = mask_personal_data(
        raw_text=ext_result.text,
        candidate_name=candidate.name,
        candidate_email=candidate.email,
        candidate_phone=candidate.phone,
    )
    cv_file.masked_text = masked_text

    await db.commit()

    # 5. Check if active scorecard exists for requisition; if so, enqueue score_cv
    sc_query = select(Scorecard).where(
        Scorecard.requisition_id == requisition_id,
        Scorecard.is_active == True,  # noqa: E712
    )
    sc = (await db.execute(sc_query)).scalar_one_or_none()
    if sc:
        # Fetch or create application
        app_q = select(Application).where(
            Application.candidate_id == candidate_id,
            Application.requisition_id == requisition_id,
        )
        app_obj = (await db.execute(app_q)).scalar_one_or_none()
        if app_obj:
            from app.jobs.queue import enqueue_job

            await enqueue_job(
                db=db,
                job_type="score_cv",
                payload={"application_id": app_obj.id, "requisition_id": requisition_id},
                batch_id=batch_id,
            )


async def handle_score_cv(db: AsyncSession, payload: dict[str, Any], batch_id: int | None) -> None:
    application_id = payload["application_id"]
    from app.ai.scoring import evaluate_and_score_application

    await evaluate_and_score_application(db, application_id)


JOB_HANDLERS = {
    "parse_cv": handle_parse_cv,
    "score_cv": handle_score_cv,
}

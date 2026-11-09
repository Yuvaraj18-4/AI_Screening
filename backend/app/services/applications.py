from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.scoring import evaluate_and_score_application
from app.core.errors import NotFoundError
from app.db.models import (
    Application,
    Criterion,
    CriterionResult,
    CVFile,
    PipelineEvent,
    Requisition,
    Score,
    User,
    ViewLog,
)
from app.services.scoping import visible_applications_for


async def list_applications_for_requisition(
    db: AsyncSession,
    requisition_id: int,
    user: User,
    sort: str = "score",
    stage: str | None = None,
) -> list[dict[str, Any]]:
    base_q = (
        visible_applications_for(user)
        .where(Application.requisition_id == requisition_id)
        .options(
            selectinload(Application.candidate),
            selectinload(Application.scores)
            .selectinload(Score.criterion_results)
            .selectinload(CriterionResult.criterion),
        )
    )

    if stage and stage.strip() and stage.lower() != "all":
        base_q = base_q.where(Application.stage == stage.lower().strip())

    res = await db.execute(base_q)
    applications = res.scalars().all()

    # Query view logs for this user to check has_viewed
    v_query = select(ViewLog.application_id).where(
        ViewLog.user_id == user.id,
        ViewLog.application_id.isnot(None),
    )
    v_res = await db.execute(v_query)
    viewed_app_ids = set(v_res.scalars().all())

    output = []
    for app in applications:
        cand = app.candidate
        latest_score = app.scores[-1] if app.scores else None

        score_dict = None
        if latest_score:
            # Determine must-have gaps
            gaps = []
            results_detail = []
            for cr in latest_score.criterion_results:
                crit = cr.criterion or await db.get(Criterion, cr.criterion_id)
                crit_name = crit.name if crit else f"Criterion #{cr.criterion_id}"
                must_have = crit.must_have if crit else False
                weight = crit.weight if crit else 1
                kind = crit.kind if crit else "skill"

                if must_have and cr.value < 1.0:
                    gaps.append(crit_name)

                results_detail.append(
                    {
                        "id": cr.id,
                        "criterion_id": cr.criterion_id,
                        "criterion_name": crit_name,
                        "kind": kind,
                        "must_have": must_have,
                        "weight": weight,
                        "verdict": cr.verdict,
                        "value": cr.value,
                        "quote": cr.quote,
                        "quote_verified": cr.quote_verified,
                        "confidence": cr.confidence,
                        "source": cr.source,
                    }
                )

            score_dict = {
                "id": latest_score.id,
                "scorecard_version": latest_score.scorecard_version,
                "total": latest_score.total,
                "confidence": latest_score.confidence,
                "status": latest_score.status,
                "scoring_mode": latest_score.scoring_mode,
                "must_have_gaps": gaps,
                "results": results_detail,
            }

        output.append(
            {
                "id": app.id,
                "candidate_id": cand.id,
                "requisition_id": app.requisition_id,
                "candidate_name": cand.name,
                "candidate_email": cand.email,
                "candidate_phone": cand.phone,
                "current_role": cand.current_role,
                "location": cand.location,
                "experience_years": cand.experience_years,
                "notice_days": cand.notice_days,
                "stage": app.stage,
                "parse_quality": cand.parse_quality,
                "duplicate_of_id": cand.duplicate_of_id,
                "has_viewed": app.id in viewed_app_ids,
                "score": score_dict,
                "created_at": app.created_at,
            }
        )

    # Sort
    if sort == "name":
        output.sort(key=lambda x: x["candidate_name"].lower())
    elif sort == "stage":
        output.sort(key=lambda x: x["stage"])
    else:  # default score
        output.sort(
            key=lambda x: (
                x["score"]["total"] if x["score"] else -1.0,
                x["experience_years"],
            ),
            reverse=True,
        )

    return output


async def get_application_detail(
    db: AsyncSession,
    application_id: int,
    user: User,
    record_view: bool = True,
) -> dict[str, Any]:
    query = (
        visible_applications_for(user)
        .where(Application.id == application_id)
        .options(
            selectinload(Application.candidate),
            selectinload(Application.requisition).selectinload(Requisition.client),
            selectinload(Application.scores)
            .selectinload(Score.criterion_results)
            .selectinload(CriterionResult.criterion),
        )
    )
    result = await db.execute(query)
    app = result.scalars().first()
    if not app:
        raise NotFoundError("Application not found or access forbidden")

    cand = app.candidate
    req = app.requisition

    # Record view log
    if record_view:
        view_log = ViewLog(
            user_id=user.id,
            candidate_id=cand.id,
            application_id=app.id,
            context="recruiter_detail" if user.role == "recruiter" else "client_portal",
        )
        db.add(view_log)
        await db.commit()

    # Get CV file text
    cv_query = select(CVFile).where(CVFile.candidate_id == cand.id).order_by(CVFile.id.desc())
    cv_file = (await db.execute(cv_query)).scalars().first()

    latest_score = app.scores[-1] if app.scores else None
    score_dict = None
    if latest_score:
        gaps = []
        results_detail = []
        for cr in latest_score.criterion_results:
            crit = cr.criterion or await db.get(Criterion, cr.criterion_id)
            crit_name = crit.name if crit else f"Criterion #{cr.criterion_id}"
            must_have = crit.must_have if crit else False
            weight = crit.weight if crit else 1
            kind = crit.kind if crit else "skill"

            if must_have and cr.value < 1.0:
                gaps.append(crit_name)

            results_detail.append(
                {
                    "id": cr.id,
                    "criterion_id": cr.criterion_id,
                    "criterion_name": crit_name,
                    "kind": kind,
                    "must_have": must_have,
                    "weight": weight,
                    "verdict": cr.verdict,
                    "value": cr.value,
                    "quote": cr.quote,
                    "quote_verified": cr.quote_verified,
                    "confidence": cr.confidence,
                    "source": cr.source,
                }
            )

        score_dict = {
            "id": latest_score.id,
            "scorecard_version": latest_score.scorecard_version,
            "total": latest_score.total,
            "confidence": latest_score.confidence,
            "status": latest_score.status,
            "scoring_mode": latest_score.scoring_mode,
            "must_have_gaps": gaps,
            "results": results_detail,
        }

    return {
        "id": app.id,
        "candidate_id": cand.id,
        "requisition_id": app.requisition_id,
        "requisition_title": req.title,
        "client_name": req.client.name if req.client else "",
        "candidate_name": cand.name,
        "candidate_email": cand.email,
        "candidate_phone": cand.phone,
        "current_role": cand.current_role,
        "location": cand.location,
        "skills": cand.skills,
        "employment": cand.employment,
        "experience_years": cand.experience_years,
        "notice_days": cand.notice_days,
        "current_ctc": cand.current_ctc,
        "expected_ctc": cand.expected_ctc,
        "education": cand.education,
        "parse_quality": cand.parse_quality,
        "duplicate_of_id": cand.duplicate_of_id,
        "stage": app.stage,
        "cv_text": cv_file.text if cv_file else "",
        "masked_text": cv_file.masked_text if cv_file else "",
        "has_viewed": True,
        "score": score_dict,
        "created_at": app.created_at,
    }


async def update_application_stage(
    db: AsyncSession,
    application_id: int,
    new_stage: str,
    user_id: int,
    note: str | None = None,
) -> dict[str, Any]:
    app = await db.get(Application, application_id)
    if not app:
        raise NotFoundError("Application not found")

    old_stage = app.stage
    app.stage = new_stage

    event = PipelineEvent(
        application_id=app.id,
        from_stage=old_stage,
        to_stage=new_stage,
        actor_id=user_id,
        note=note,
    )
    db.add(event)
    await db.commit()
    user = await db.get(User, user_id)
    return await get_application_detail(db, application_id, user, record_view=False)


async def rescore_application(
    db: AsyncSession, application_id: int, user_id: int
) -> dict[str, Any]:
    await evaluate_and_score_application(db, application_id, force_rescore=True)
    user = await db.get(User, user_id)
    return await get_application_detail(db, application_id, user, record_view=False)

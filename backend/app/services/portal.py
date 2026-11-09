from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, ValidationError
from app.db.models.entities import (
    Application,
    CriterionResult,
    PipelineEvent,
    Requisition,
    Score,
    Submission,
    User,
    ViewLog,
)
from app.schemas.candidates import CriterionResultDetail
from app.schemas.portal import (
    PortalDecisionIn,
    PortalRequisitionOut,
    PortalSubmissionDetailOut,
    PortalSubmissionListItem,
)


def _check_client_access(user: User, resource_client_id: int | None) -> None:
    if user.role == "client" and (not user.client_id or user.client_id != resource_client_id):
        raise NotFoundError("Resource not found")


async def list_portal_requisitions(db: AsyncSession, user: User) -> list[PortalRequisitionOut]:
    """List requisitions for client user that have submissions."""
    if user.role == "client" and not user.client_id:
        return []

    query = select(Requisition)
    if user.role == "client":
        query = query.where(Requisition.client_id == user.client_id)

    result = await db.execute(query.order_by(desc(Requisition.created_at)))
    reqs = result.scalars().all()

    out = []
    for r in reqs:
        cnt_res = await db.execute(
            select(func.count(Submission.id))
            .join(Application, Submission.application_id == Application.id)
            .where(Application.requisition_id == r.id)
        )
        count = cnt_res.scalar() or 0
        if count > 0 or user.role == "recruiter":
            out.append(
                PortalRequisitionOut(
                    id=r.id,
                    title=r.title,
                    department=None,
                    location=None,
                    status=r.status,
                    submission_count=count,
                )
            )
    return out


async def list_portal_submissions(
    db: AsyncSession,
    requisition_id: int,
    user: User,
) -> list[PortalSubmissionListItem]:
    """List submissions for a requisition visible to the client."""
    req = await db.get(Requisition, requisition_id)
    if not req:
        raise NotFoundError(f"Requisition {requisition_id} not found")

    _check_client_access(user, req.client_id)

    query = (
        select(Submission)
        .join(Application, Submission.application_id == Application.id)
        .options(
            selectinload(Submission.application).selectinload(Application.candidate),
            selectinload(Submission.application)
            .selectinload(Application.scores)
            .selectinload(Score.criterion_results)
            .selectinload(CriterionResult.criterion),
        )
        .where(Application.requisition_id == requisition_id)
        .order_by(desc(Submission.submitted_at))
    )
    result = await db.execute(query)
    submissions = result.scalars().all()

    items: list[PortalSubmissionListItem] = []
    for sub in submissions:
        app = sub.application
        cand = app.candidate if app else None
        if not cand:
            continue

        latest_score = app.scores[0] if app and app.scores else None
        unmasked = app.stage in {"client_shortlisted", "interview", "offered", "joined"}

        # Find must-have gaps from criterion results
        gaps: list[str] = []
        if latest_score and latest_score.criterion_results:
            for cr in latest_score.criterion_results:
                if cr.criterion and cr.criterion.must_have and cr.verdict not in ("met", "partial"):
                    gaps.append(cr.criterion.name)

        items.append(
            PortalSubmissionListItem(
                submission_id=sub.id,
                application_id=app.id if app else 0,
                candidate_id=cand.id,
                candidate_name=cand.name,
                candidate_email=cand.email if unmasked else "[MASKED_UNTIL_SHORTLIST]",
                candidate_phone=cand.phone
                if (unmasked and cand.phone)
                else "[MASKED_UNTIL_SHORTLIST]",
                stage=app.stage if app else sub.client_decision,
                client_decision=sub.client_decision,
                submitted_at=sub.submitted_at,
                weighted_score=latest_score.total if latest_score else None,
                must_have_gaps=gaps,
                confidence_score=latest_score.confidence if latest_score else None,
                notes=None,
            )
        )
    return items


async def get_portal_submission_detail(
    db: AsyncSession,
    submission_id: int,
    user: User,
) -> PortalSubmissionDetailOut:
    """Retrieve detailed submission view for client with view logging and contact masking."""
    query = (
        select(Submission)
        .options(
            selectinload(Submission.application).selectinload(Application.requisition),
            selectinload(Submission.application).selectinload(Application.candidate),
            selectinload(Submission.application)
            .selectinload(Application.scores)
            .selectinload(Score.criterion_results)
            .selectinload(CriterionResult.criterion),
        )
        .where(Submission.id == submission_id)
    )
    result = await db.execute(query)
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundError(f"Submission {submission_id} not found")

    app = sub.application
    req = app.requisition if app else None
    cand = app.candidate if app else None
    if not req or not cand or not app:
        raise NotFoundError("Submission data incomplete")

    _check_client_access(user, req.client_id)

    # Log ViewLog for client portal
    view = ViewLog(
        user_id=user.id,
        candidate_id=cand.id,
        application_id=app.id,
        context="portal",
    )
    db.add(view)
    await db.commit()

    latest_score = app.scores[0] if app.scores else None
    unmasked = app.stage in {"client_shortlisted", "interview", "offered", "joined"}

    criteria_out: list[CriterionResultDetail] = []
    gaps: list[str] = []
    if latest_score and latest_score.criterion_results:
        for cr in latest_score.criterion_results:
            crit = cr.criterion
            if crit and crit.must_have and cr.verdict not in ("met", "partial"):
                gaps.append(crit.name)
            criteria_out.append(
                CriterionResultDetail(
                    id=cr.id,
                    criterion_id=cr.criterion_id,
                    criterion_name=crit.name if crit else "Criterion",
                    kind=crit.kind if crit else "skill",
                    must_have=crit.must_have if crit else False,
                    weight=crit.weight if crit else 1,
                    verdict=cr.verdict,
                    value=cr.value,
                    quote=cr.quote,
                    quote_verified=cr.quote_verified,
                    confidence=cr.confidence,
                    source=cr.source,
                )
            )

    return PortalSubmissionDetailOut(
        submission_id=sub.id,
        application_id=app.id,
        candidate_id=cand.id,
        candidate_name=cand.name,
        candidate_email=cand.email if unmasked else "[MASKED_UNTIL_SHORTLIST]",
        candidate_phone=cand.phone if (unmasked and cand.phone) else "[MASKED_UNTIL_SHORTLIST]",
        stage=app.stage,
        client_decision=sub.client_decision,
        submitted_at=sub.submitted_at,
        weighted_score=latest_score.total if latest_score else None,
        must_have_gaps=gaps,
        confidence_score=latest_score.confidence if latest_score else None,
        notes=None,
        proposed_slot=sub.proposed_slot,
        reject_reason=sub.reject_reason,
        masked=not unmasked,
        criteria_results=criteria_out,
    )


async def decide_portal_submission(
    db: AsyncSession,
    submission_id: int,
    payload: PortalDecisionIn,
    user: User,
) -> PortalSubmissionDetailOut:
    """Record client decision: shortlisted, rejected (with required reason), or propose_slot."""
    query = (
        select(Submission)
        .options(
            selectinload(Submission.application).selectinload(Application.requisition),
            selectinload(Submission.application),
        )
        .where(Submission.id == submission_id)
    )
    result = await db.execute(query)
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundError(f"Submission {submission_id} not found")

    app = sub.application
    req = app.requisition if app else None
    if not req or not app:
        raise NotFoundError("Application data incomplete")

    _check_client_access(user, req.client_id)

    from_stage = app.stage

    if payload.decision == "rejected":
        if not payload.reject_reason or not payload.reject_reason.strip():
            raise ValidationError("Rejection reason is required")
        sub.client_decision = "rejected"
        sub.reject_reason = payload.reject_reason.strip()
        sub.decided_by = user.id
        sub.decided_at = datetime.now(UTC)
        app.stage = "rejected"
    elif payload.decision == "shortlisted":
        sub.client_decision = "shortlisted"
        sub.decided_by = user.id
        sub.decided_at = datetime.now(UTC)
        app.stage = "client_shortlisted"
    elif payload.decision == "propose_slot":
        if not payload.proposed_slot:
            raise ValidationError("Proposed interview slot is required")
        sub.client_decision = "shortlisted"
        sub.proposed_slot = payload.proposed_slot
        sub.decided_by = user.id
        sub.decided_at = datetime.now(UTC)
        app.stage = "interview"

    # Add PipelineEvent
    event = PipelineEvent(
        application_id=app.id,
        from_stage=from_stage,
        to_stage=app.stage,
        actor_id=user.id,
        note=payload.notes or f"Client decision: {payload.decision}",
        created_at=datetime.now(UTC),
    )
    db.add(event)
    await db.commit()

    return await get_portal_submission_detail(db, submission_id, user)

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError
from app.db.models import Application, PipelineEvent, Submission, User, ViewLog


async def submit_application_to_client(
    db: AsyncSession,
    application_id: int,
    user: User,
) -> dict[str, Any]:
    # 1. Fetch application
    query = (
        select(Application)
        .options(
            selectinload(Application.candidate),
            selectinload(Application.requisition),
            selectinload(Application.submissions),
        )
        .where(Application.id == application_id)
    )
    res = await db.execute(query)
    app = res.scalars().first()
    if not app:
        raise NotFoundError("Application not found")

    # 2. Check server-side view enforcement (ViewLog)
    view_query = select(ViewLog).where(
        ViewLog.user_id == user.id,
        ViewLog.application_id == application_id,
    )
    view_res = await db.execute(view_query)
    has_viewed = view_res.scalars().first() is not None

    if not has_viewed:
        raise ConflictError(
            "Candidate application must be opened and reviewed before client submission (view-before-submit rule)"
        )

    # 3. Check if already submitted
    sub_check_q = select(Submission).where(
        Submission.application_id == application_id,
        Submission.client_decision != "rejected",
    )
    existing_sub = (await db.execute(sub_check_q)).scalars().first()
    if existing_sub:
        raise ConflictError("This candidate has already been submitted to the client")

    now = datetime.now(UTC)
    old_stage = app.stage
    app.stage = "submitted"

    submission = Submission(
        application_id=app.id,
        submitted_by=user.id,
        submitted_at=now,
        client_decision="pending",
    )
    db.add(submission)

    event = PipelineEvent(
        application_id=app.id,
        from_stage=old_stage,
        to_stage="submitted",
        actor_id=user.id,
        note="Submitted by recruiter to client review portal",
    )
    db.add(event)

    await db.commit()
    await db.refresh(submission)

    return {
        "id": submission.id,
        "application_id": app.id,
        "submitted_by": user.id,
        "submitted_at": submission.submitted_at,
        "client_decision": submission.client_decision,
        "reject_reason": submission.reject_reason,
        "decided_by": submission.decided_by,
        "decided_at": submission.decided_at,
        "proposed_slot": submission.proposed_slot,
        "candidate_name": app.candidate.name,
        "requisition_title": app.requisition.title,
    }

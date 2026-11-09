from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, verify_csrf
from app.core.errors import NotFoundError
from app.db.models.entities import Candidate, Consent, User
from app.schemas.consent import ConsentOut, ConsentRecordIn

router = APIRouter(prefix="/candidates", tags=["consent"])


@router.post(
    "/{candidate_id}/consent",
    response_model=ConsentOut,
    dependencies=[Depends(verify_csrf)],
)
async def record_candidate_consent(
    candidate_id: int,
    payload: ConsentRecordIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> ConsentOut:
    cand = await db.get(Candidate, candidate_id)
    if not cand:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    now = datetime.now(UTC)
    consent = Consent(
        candidate_id=candidate_id,
        source=payload.channel,
        given_at=now,
        recorded_by=current_user.id,
        revoked_at=None,
    )
    db.add(consent)
    await db.commit()

    return ConsentOut(
        candidate_id=str(cand.id),
        consent_status="granted",
        consented_at=now,
        revoked_at=None,
    )


@router.delete(
    "/{candidate_id}/consent",
    response_model=ConsentOut,
    dependencies=[Depends(verify_csrf)],
)
async def revoke_candidate_consent(
    candidate_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> ConsentOut:
    cand = await db.get(Candidate, candidate_id)
    if not cand:
        raise NotFoundError(f"Candidate {candidate_id} not found")

    result = await db.execute(
        select(Consent)
        .where(Consent.candidate_id == candidate_id, Consent.revoked_at.is_(None))
        .order_by(Consent.given_at.desc())
    )
    active_consent = result.scalars().first()
    now = datetime.now(UTC)
    if active_consent:
        active_consent.revoked_at = now
        await db.commit()

    return ConsentOut(
        candidate_id=str(cand.id),
        consent_status="revoked",
        consented_at=active_consent.given_at if active_consent else None,
        revoked_at=now,
    )

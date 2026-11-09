from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, ValidationError
from app.db.models import Criterion, Requisition, Scorecard


async def get_active_scorecard(db: AsyncSession, req_id: int) -> Scorecard | None:
    req = await db.get(Requisition, req_id)
    if not req:
        raise NotFoundError("Requisition not found")

    query = (
        select(Scorecard)
        .options(selectinload(Scorecard.criteria))
        .where(
            Scorecard.requisition_id == req_id,
            Scorecard.is_active == True,  # noqa: E712
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def save_new_scorecard_version(
    db: AsyncSession,
    req_id: int,
    criteria_list: list[dict[str, Any]],
) -> Scorecard:
    req = await db.get(Requisition, req_id)
    if not req:
        raise NotFoundError("Requisition not found")

    if not criteria_list:
        raise ValidationError("Scorecard must contain at least one criterion")

    # Determine next version
    v_query = (
        select(Scorecard.version)
        .where(Scorecard.requisition_id == req_id)
        .order_by(Scorecard.version.desc())
    )
    v_res = await db.execute(v_query)
    latest_version = v_res.scalars().first()
    next_version = (latest_version or 0) + 1

    # Deactivate prior scorecards
    await db.execute(
        update(Scorecard).where(Scorecard.requisition_id == req_id).values(is_active=False)
    )

    # Create new active scorecard
    scorecard = Scorecard(
        requisition_id=req_id,
        version=next_version,
        is_active=True,
    )
    db.add(scorecard)
    await db.flush()

    for item in criteria_list:
        crit = Criterion(
            scorecard_id=scorecard.id,
            name=item["name"],
            kind=item["kind"],
            must_have=item.get("must_have", False),
            weight=item.get("weight", 1),
            params=item.get("params", {}),
            description=item.get("description", ""),
        )
        db.add(crit)

    await db.commit()

    # Refresh with loaded criteria
    return await get_active_scorecard(db, req_id)

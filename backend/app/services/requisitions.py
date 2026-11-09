from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import get_llm_client
from app.core.errors import NotFoundError
from app.db.models import Application, Client, Requisition, Scorecard


async def list_requisitions(db: AsyncSession) -> list[dict[str, Any]]:
    # Query requisitions with client name, application count, and active scorecard version
    query = (
        select(
            Requisition,
            Client.name.label("client_name"),
            func.count(Application.id).label("apps_count"),
        )
        .join(Client, Client.id == Requisition.client_id)
        .outerjoin(Application, Application.requisition_id == Requisition.id)
        .group_by(Requisition.id, Client.name)
        .order_by(Requisition.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    output = []
    for req, client_name, apps_count in rows:
        # Get active scorecard version if any
        sc_query = select(Scorecard.version).where(
            Scorecard.requisition_id == req.id,
            Scorecard.is_active == True,  # noqa: E712
        )
        sc_res = await db.execute(sc_query)
        sc_version = sc_res.scalar_one_or_none()

        output.append(
            {
                "id": req.id,
                "client_id": req.client_id,
                "title": req.title,
                "jd_text": req.jd_text,
                "status": req.status,
                "owner_id": req.owner_id,
                "client_name": client_name,
                "applications_count": apps_count,
                "active_scorecard_version": sc_version,
                "created_at": req.created_at,
            }
        )
    return output


async def get_requisition(db: AsyncSession, req_id: int) -> dict[str, Any]:
    query = (
        select(Requisition, Client.name.label("client_name"))
        .join(Client, Client.id == Requisition.client_id)
        .where(Requisition.id == req_id)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise NotFoundError("Requisition not found")

    req, client_name = row
    app_count_res = await db.execute(
        select(func.count(Application.id)).where(Application.requisition_id == req.id)
    )
    apps_count = app_count_res.scalar_one()

    sc_query = select(Scorecard.version).where(
        Scorecard.requisition_id == req.id,
        Scorecard.is_active == True,  # noqa: E712
    )
    sc_version = (await db.execute(sc_query)).scalar_one_or_none()

    return {
        "id": req.id,
        "client_id": req.client_id,
        "title": req.title,
        "jd_text": req.jd_text,
        "status": req.status,
        "owner_id": req.owner_id,
        "client_name": client_name,
        "applications_count": apps_count,
        "active_scorecard_version": sc_version,
        "created_at": req.created_at,
    }


async def create_requisition(
    db: AsyncSession,
    client_id: int,
    title: str,
    jd_text: str,
    owner_id: int,
) -> dict[str, Any]:
    client = await db.get(Client, client_id)
    if not client:
        raise NotFoundError("Client organization not found")

    req = Requisition(
        client_id=client_id,
        title=title.strip(),
        jd_text=jd_text.strip(),
        status="draft",
        owner_id=owner_id,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return await get_requisition(db, req.id)


async def update_requisition(
    db: AsyncSession,
    req_id: int,
    title: str | None = None,
    jd_text: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    req = await db.get(Requisition, req_id)
    if not req:
        raise NotFoundError("Requisition not found")

    if title is not None:
        req.title = title.strip()
    if jd_text is not None:
        req.jd_text = jd_text.strip()
    if status is not None:
        req.status = status

    await db.commit()
    return await get_requisition(db, req_id)


async def extract_jd_criteria(db: AsyncSession, req_id: int) -> dict[str, Any]:
    req = await db.get(Requisition, req_id)
    if not req:
        raise NotFoundError("Requisition not found")

    if not req.jd_text or not req.jd_text.strip():
        raise NotFoundError("Requisition does not have job description text")

    llm = get_llm_client()
    extracted = await llm.extract_jd(req.jd_text)

    # If title returned and current title is generic or empty, can update or return
    return extracted

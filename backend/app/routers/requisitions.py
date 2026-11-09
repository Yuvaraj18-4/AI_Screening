from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, verify_csrf
from app.db.models import User
from app.schemas.requisitions import RequisitionCreate, RequisitionOut, RequisitionUpdate
from app.schemas.scorecards import JDExtractResponse
from app.services import requisitions as req_service

router = APIRouter(prefix="/requisitions", tags=["requisitions"])


@router.get("", response_model=list[RequisitionOut])
async def list_requisitions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> list[RequisitionOut]:
    data = await req_service.list_requisitions(db)
    return [RequisitionOut.model_validate(item) for item in data]


@router.post("", response_model=RequisitionOut, dependencies=[Depends(verify_csrf)])
async def create_requisition(
    payload: RequisitionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> RequisitionOut:
    data = await req_service.create_requisition(
        db=db,
        client_id=payload.client_id,
        title=payload.title,
        jd_text=payload.jd_text,
        owner_id=current_user.id,
    )
    return RequisitionOut.model_validate(data)


@router.get("/{req_id}", response_model=RequisitionOut)
async def get_requisition(
    req_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> RequisitionOut:
    data = await req_service.get_requisition(db, req_id)
    return RequisitionOut.model_validate(data)


@router.patch("/{req_id}", response_model=RequisitionOut, dependencies=[Depends(verify_csrf)])
async def update_requisition(
    req_id: int,
    payload: RequisitionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> RequisitionOut:
    data = await req_service.update_requisition(
        db=db,
        req_id=req_id,
        title=payload.title,
        jd_text=payload.jd_text,
        status=payload.status,
    )
    return RequisitionOut.model_validate(data)


@router.post(
    "/{req_id}/jd/extract", response_model=JDExtractResponse, dependencies=[Depends(verify_csrf)]
)
async def extract_jd(
    req_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> JDExtractResponse:
    data = await req_service.extract_jd_criteria(db, req_id)
    return JDExtractResponse.model_validate(data)

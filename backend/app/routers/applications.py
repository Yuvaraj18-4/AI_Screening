from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, verify_csrf
from app.db.models import User
from app.schemas.candidates import (
    ApplicationDetailOut,
    ApplicationListItem,
    StageUpdateRequest,
)
from app.schemas.submissions import SubmissionOut
from app.services import applications as app_service
from app.services import submissions as sub_service

router = APIRouter(tags=["applications"])


@router.get("/requisitions/{req_id}/applications", response_model=list[ApplicationListItem])
async def list_requisition_applications(
    req_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
    sort: str = Query("score", pattern="^(score|name|stage)$"),
    stage: str | None = Query(None),
) -> list[ApplicationListItem]:
    data = await app_service.list_applications_for_requisition(
        db=db,
        requisition_id=req_id,
        user=current_user,
        sort=sort,
        stage=stage,
    )
    return [ApplicationListItem.model_validate(item) for item in data]


@router.get("/applications/{app_id}", response_model=ApplicationDetailOut)
async def get_application_detail(
    app_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> ApplicationDetailOut:
    data = await app_service.get_application_detail(
        db=db,
        application_id=app_id,
        user=current_user,
        record_view=True,
    )
    return ApplicationDetailOut.model_validate(data)


@router.post(
    "/applications/{app_id}/submit",
    response_model=SubmissionOut,
    dependencies=[Depends(verify_csrf)],
)
async def submit_application(
    app_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> SubmissionOut:
    data = await sub_service.submit_application_to_client(
        db=db,
        application_id=app_id,
        user=current_user,
    )
    return SubmissionOut.model_validate(data)


@router.post(
    "/applications/{app_id}/rescore",
    response_model=ApplicationDetailOut,
    dependencies=[Depends(verify_csrf)],
)
async def rescore_application(
    app_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> ApplicationDetailOut:
    data = await app_service.rescore_application(
        db=db,
        application_id=app_id,
        user_id=current_user.id,
    )
    return ApplicationDetailOut.model_validate(data)


@router.post(
    "/applications/{app_id}/stage",
    response_model=ApplicationDetailOut,
    dependencies=[Depends(verify_csrf)],
)
async def update_application_stage(
    app_id: int,
    payload: StageUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> ApplicationDetailOut:
    data = await app_service.update_application_stage(
        db=db,
        application_id=app_id,
        new_stage=payload.stage,
        user_id=current_user.id,
        note=payload.note,
    )
    return ApplicationDetailOut.model_validate(data)

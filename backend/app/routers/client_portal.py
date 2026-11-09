from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, verify_csrf
from app.db.models.entities import User
from app.schemas.portal import (
    PortalDecisionIn,
    PortalRequisitionOut,
    PortalSubmissionDetailOut,
    PortalSubmissionListItem,
)
from app.services.portal import (
    decide_portal_submission,
    get_portal_submission_detail,
    list_portal_requisitions,
    list_portal_submissions,
)

router = APIRouter(prefix="/portal", tags=["client_portal"])


@router.get("/requisitions", response_model=list[PortalRequisitionOut])
async def get_portal_requisitions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("client", "recruiter"))],
) -> list[PortalRequisitionOut]:
    return await list_portal_requisitions(db, current_user)


@router.get(
    "/requisitions/{requisition_id}/submissions", response_model=list[PortalSubmissionListItem]
)
async def get_portal_requisition_submissions(
    requisition_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("client", "recruiter"))],
) -> list[PortalSubmissionListItem]:
    return await list_portal_submissions(db, requisition_id, current_user)


@router.get("/submissions/{submission_id}", response_model=PortalSubmissionDetailOut)
async def get_submission(
    submission_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("client", "recruiter"))],
) -> PortalSubmissionDetailOut:
    return await get_portal_submission_detail(db, submission_id, current_user)


@router.post(
    "/submissions/{submission_id}/decision",
    response_model=PortalSubmissionDetailOut,
    dependencies=[Depends(verify_csrf)],
)
async def submit_decision(
    submission_id: int,
    payload: PortalDecisionIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("client", "recruiter"))],
) -> PortalSubmissionDetailOut:
    return await decide_portal_submission(db, submission_id, payload, current_user)

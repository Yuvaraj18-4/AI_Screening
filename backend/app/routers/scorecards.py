from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, verify_csrf
from app.core.errors import NotFoundError
from app.db.models import User
from app.schemas.scorecards import ScorecardCreate, ScorecardOut
from app.services import scorecards as sc_service

router = APIRouter(tags=["scorecards"])


@router.get("/requisitions/{req_id}/scorecard", response_model=ScorecardOut)
async def get_scorecard(
    req_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> ScorecardOut:
    scorecard = await sc_service.get_active_scorecard(db, req_id)
    if not scorecard:
        raise NotFoundError("Scorecard not found for requisition")
    return ScorecardOut.model_validate(scorecard)


@router.put(
    "/requisitions/{req_id}/scorecard",
    response_model=ScorecardOut,
    dependencies=[Depends(verify_csrf)],
)
@router.post(
    "/requisitions/{req_id}/scorecard",
    response_model=ScorecardOut,
    dependencies=[Depends(verify_csrf)],
)
async def update_scorecard(
    req_id: int,
    payload: ScorecardCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> ScorecardOut:
    criteria_data = [item.model_dump() for item in payload.criteria]
    scorecard = await sc_service.save_new_scorecard_version(db, req_id, criteria_data)
    return ScorecardOut.model_validate(scorecard)

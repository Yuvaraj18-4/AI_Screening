from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, verify_csrf
from app.db.models import User
from app.schemas.candidates import DuplicateResolutionRequest
from app.services import candidates as cand_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post(
    "/{candidate_id}/duplicate-resolution",
    dependencies=[Depends(verify_csrf)],
)
async def resolve_duplicate(
    candidate_id: int,
    payload: DuplicateResolutionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> dict[str, Any]:
    return await cand_service.resolve_candidate_duplicate(
        db=db,
        candidate_id=candidate_id,
        action=payload.action,
    )


@router.delete(
    "/{candidate_id}",
    dependencies=[Depends(verify_csrf)],
)
async def delete_candidate(
    candidate_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> dict[str, Any]:
    return await cand_service.delete_candidate_on_request(
        db=db,
        candidate_id=candidate_id,
        actor_id=current_user.id,
    )

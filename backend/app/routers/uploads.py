from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role, verify_csrf
from app.db.models import User
from app.schemas.uploads import BatchProgressOut, UploadResponse
from app.services import uploads as upload_service

router = APIRouter(tags=["uploads"])


@router.post(
    "/requisitions/{req_id}/uploads",
    response_model=UploadResponse,
    dependencies=[Depends(verify_csrf)],
)
async def upload_cv_files(
    req_id: int,
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> UploadResponse:
    file_tuples = []
    for f in files:
        content = await f.read()
        file_tuples.append((f.filename or "unknown.pdf", content))

    result = await upload_service.process_cv_uploads(
        db=db,
        requisition_id=req_id,
        user_id=current_user.id,
        file_tuples=file_tuples,
    )
    return UploadResponse.model_validate(result)


@router.get(
    "/uploads/{batch_id}/progress",
    response_model=BatchProgressOut,
)
async def get_upload_progress(
    batch_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("recruiter"))],
) -> BatchProgressOut:
    progress = await upload_service.get_batch_progress(db, batch_id)
    return BatchProgressOut.model_validate(progress)

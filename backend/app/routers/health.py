from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.schemas.auth import HealthOut

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthOut)
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> HealthOut:
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return HealthOut(
        status="ok",
        database=db_status,
        scoring_mode="llm" if settings.has_gemini_key else "heuristic",
        worker_status="running",
    )

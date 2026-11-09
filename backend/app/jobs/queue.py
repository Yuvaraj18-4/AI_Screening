from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job


def _utc_now() -> datetime:
    # Use timezone-aware UTC datetime
    return datetime.now(UTC)


async def enqueue_job(
    db: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
    batch_id: int | None = None,
    max_attempts: int = 3,
) -> Job:
    now = _utc_now()
    job = Job(
        type=job_type,
        payload=payload,
        status="queued",
        attempts=0,
        max_attempts=max_attempts,
        next_run_at=now,
        batch_id=batch_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def claim_next_job(db: AsyncSession) -> Job | None:
    now = _utc_now()

    subq = (
        select(Job.id)
        .where(
            Job.status == "queued",
            Job.next_run_at <= now,
        )
        .order_by(Job.created_at.asc())
        .limit(1)
    )
    res = await db.execute(subq)
    job_id = res.scalar_one_or_none()

    if not job_id:
        return None

    stmt = (
        update(Job)
        .where(Job.id == job_id, Job.status == "queued")
        .values(
            status="running",
            attempts=Job.attempts + 1,
            started_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    update_res = await db.execute(stmt)
    await db.commit()

    if update_res.rowcount > 0:
        query = select(Job).where(Job.id == job_id).execution_options(populate_existing=True)
        res = await db.execute(query)
        return res.scalar_one_or_none()

    return None


async def finish_job(
    db: AsyncSession,
    job_id: int,
    status: str,
    error_message: str | None = None,
) -> None:
    now = _utc_now()
    stmt = (
        update(Job)
        .where(Job.id == job_id)
        .values(
            status=status,
            finished_at=now,
            last_error=error_message,
        )
        .execution_options(synchronize_session=False)
    )
    await db.execute(stmt)
    await db.commit()


async def fail_or_retry_job(
    db: AsyncSession,
    job_id: int,
    error_message: str,
) -> None:
    query = select(Job).where(Job.id == job_id).execution_options(populate_existing=True)
    res = await db.execute(query)
    job = res.scalar_one_or_none()
    if not job:
        return

    now = _utc_now()
    if job.attempts < job.max_attempts:
        backoff_seconds = 5 * (4 ** (job.attempts - 1))
        next_run = now + timedelta(seconds=backoff_seconds)
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(
                status="queued",
                next_run_at=next_run,
                last_error=error_message,
            )
            .execution_options(synchronize_session=False)
        )
    else:
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(
                status="failed",
                finished_at=now,
                last_error=error_message,
            )
            .execution_options(synchronize_session=False)
        )
    await db.execute(stmt)
    await db.commit()


async def reset_stale_running_jobs(db: AsyncSession, timeout_seconds: int = 300) -> int:
    now = _utc_now()
    cutoff = now - timedelta(seconds=timeout_seconds)
    stmt = (
        update(Job)
        .where(
            Job.status == "running",
            Job.started_at < cutoff,
        )
        .values(
            status="queued",
            next_run_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount

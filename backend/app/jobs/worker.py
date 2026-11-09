import asyncio
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.jobs.handlers import JOB_HANDLERS
from app.jobs.queue import (
    claim_next_job,
    fail_or_retry_job,
    finish_job,
    reset_stale_running_jobs,
)

_worker_tasks: list[asyncio.Task[Any]] = []
_shutdown_event: asyncio.Event = asyncio.Event()


async def _worker_loop(worker_idx: int) -> None:
    logger.info("Worker #%d started", worker_idx)
    while not _shutdown_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                job = await claim_next_job(db)
                if not job:
                    await asyncio.sleep(0.5)
                    continue

                logger.info(
                    "Worker #%d claimed job %d (type: %s, attempt %d/%d)",
                    worker_idx,
                    job.id,
                    job.type,
                    job.attempts,
                    job.max_attempts,
                )

                handler = JOB_HANDLERS.get(job.type)
                if not handler:
                    await finish_job(db, job.id, "failed", f"No handler registered for {job.type}")
                    continue

                try:
                    await handler(db, job.payload, job.batch_id)
                    await finish_job(db, job.id, "done")
                    logger.info("Job %d completed successfully", job.id)
                except Exception as exc:
                    logger.exception("Job %d execution failed: %s", job.id, exc)
                    await fail_or_retry_job(db, job.id, str(exc))

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Unexpected worker exception: %s", exc)
            await asyncio.sleep(1.0)

    logger.info("Worker #%d stopped", worker_idx)


async def start_worker() -> list[asyncio.Task[Any]]:
    global _worker_tasks, _shutdown_event
    _shutdown_event.clear()

    # Reset any stale running jobs from prior process crash/restart
    async with AsyncSessionLocal() as db:
        try:
            reset_count = await reset_stale_running_jobs(db, timeout_seconds=300)
            if reset_count > 0:
                logger.info("Reset %d stale running jobs to queued state", reset_count)
        except Exception as exc:
            logger.warning("Failed to reset stale jobs on startup: %s", exc)

    concurrency = max(1, settings.WORKER_CONCURRENCY)
    _worker_tasks = [
        asyncio.create_task(_worker_loop(i + 1), name=f"shortlist-worker-{i + 1}")
        for i in range(concurrency)
    ]
    return _worker_tasks


async def stop_worker() -> None:
    global _worker_tasks, _shutdown_event
    _shutdown_event.set()
    for task in _worker_tasks:
        task.cancel()
    if _worker_tasks:
        await asyncio.gather(*_worker_tasks, return_exceptions=True)
    _worker_tasks.clear()
    logger.info("All background workers terminated")

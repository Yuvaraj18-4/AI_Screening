from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger
from app.routers import (
    applications,
    auth,
    candidates,
    client_portal,
    consent,
    health,
    requisitions,
    scorecards,
    submissions,
    uploads,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting ShortList service (env: %s, scoring_mode: %s)",
        settings.ENV,
        "llm" if settings.has_gemini_key else "heuristic",
    )

    # 1. Automatic database migrations
    def run_db_migrations():
        alembic_ini = Path(__file__).resolve().parent / "db" / "migrations" / "alembic.ini"
        if alembic_ini.exists():
            from alembic import command
            from alembic.config import Config

            alembic_cfg = Config(str(alembic_ini))
            alembic_cfg.set_main_option("script_location", str(alembic_ini.parent))
            command.upgrade(alembic_cfg, "head")

    try:
        import asyncio

        await asyncio.to_thread(run_db_migrations)
        logger.info("Database migrations applied successfully")
    except Exception as exc:
        logger.warning("Alembic auto-migration notice: %s; ensuring schema via metadata", exc)
        from app.db.base import Base
        from app.db.session import engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # 2. Idempotent demo data seeding if SEED_DEMO_DATA=True and no users exist
    if settings.SEED_DEMO_DATA:
        import sys
        import traceback

        from sqlalchemy import func, select

        from app.db.models import User
        from app.db.session import AsyncSessionLocal

        project_root = Path(__file__).resolve().parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        try:
            async with AsyncSessionLocal() as db:
                user_count = (await db.execute(select(func.count(User.id)))).scalar_one()
                c3_exists = (
                    await db.execute(select(User).where(User.email == "client3@example.com"))
                ).scalars().first() is not None
            if user_count == 0 or not c3_exists:
                print("SEED: DB needs updated demo data, seeding demo data...", flush=True)
                logger.info("SEED_DEMO_DATA=true and demo data update needed. Seeding demo data...")
                from scripts.seed import seed

                await seed()
                print("SEED: completed", flush=True)
                logger.info("Demo data seeding completed")
            else:
                print("SEED: updated users already exist, skipping", flush=True)
        except Exception:
            traceback.print_exc()
            logger.exception("Demo seeding failed; app will start without full demo data")

    # 3. Worker startup
    try:
        from app.jobs.worker import start_worker, stop_worker

        worker_task = await start_worker()
    except Exception as exc:
        logger.warning("Worker failed to start or not initialized yet: %s", exc)
        worker_task = None

    yield

    if worker_task:
        try:
            from app.jobs.worker import stop_worker

            await stop_worker()
        except Exception:
            pass
    logger.info("ShortList service shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ShortList API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server error: %s", exc)
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    # Include routers under /api
    app.include_router(auth.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    app.include_router(requisitions.router, prefix="/api")
    app.include_router(scorecards.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")
    app.include_router(candidates.router, prefix="/api")
    app.include_router(applications.router, prefix="/api")
    app.include_router(submissions.router, prefix="/api")
    app.include_router(client_portal.router, prefix="/api")
    app.include_router(consent.router, prefix="/api")

    # Static files mounting (Single Page App)
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path == "api" or full_path.startswith("api/"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            if full_path.startswith(".well-known/"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            file_candidate = frontend_dist / full_path
            if file_candidate.is_file():
                return FileResponse(file_candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
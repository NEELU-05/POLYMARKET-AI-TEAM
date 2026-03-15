"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.event_bus import event_bus
from app.db.database import init_db, close_db
from app.api.routes import router
from app.api.websocket import router as ws_router
from app.services.scheduler import stop_scheduler

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    setup_logging()
    settings = get_settings()
    log.info("starting", app=settings.app_name)

    # Initialize database
    await init_db()
    log.info("database_initialized")

    # Connect event bus to Redis
    await event_bus.connect()

    # Scheduler is NOT auto-started — user controls it via dashboard Start/Stop button

    yield

    # Shutdown — stop scheduler if running
    log.info("shutting_down")
    await stop_scheduler()

    await event_bus.disconnect()
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Self-learning AI multi-agent prediction market system",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(ws_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()

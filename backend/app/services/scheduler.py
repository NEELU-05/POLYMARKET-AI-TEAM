"""Background scheduler for periodic pipeline and reflection runs."""

import asyncio
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import get_async_session_factory
from app.services.orchestrator import orchestrator

log = get_logger("scheduler")

_running = False
_pipeline_task: asyncio.Task | None = None
_reflection_task: asyncio.Task | None = None
_started_at: datetime | None = None
_cycles_completed: int = 0


async def _pipeline_loop() -> None:
    """Periodically run the full prediction pipeline."""
    global _cycles_completed
    settings = get_settings()
    interval = settings.scan_interval_minutes * 60

    log.info("pipeline_loop_started", interval_minutes=settings.scan_interval_minutes)

    while _running:
        try:
            factory = get_async_session_factory()
            async with factory() as db:
                report = await orchestrator.run_full_pipeline(db)
                await db.commit()
                _cycles_completed += 1
                log.info("scheduled_pipeline_done", report=report)
        except Exception as e:
            log.error("scheduled_pipeline_error", error=str(e))

        await asyncio.sleep(interval)


async def _reflection_loop() -> None:
    """Periodically check for resolved markets and reflect."""
    settings = get_settings()
    interval = settings.resolution_check_interval_minutes * 60

    while _running:
        await asyncio.sleep(interval)
        if not _running:
            break
        try:
            factory = get_async_session_factory()
            async with factory() as db:
                result = await orchestrator.run_reflection_cycle(db)
                await db.commit()
                log.info("scheduled_reflection_done", result=result)
        except Exception as e:
            log.error("scheduled_reflection_error", error=str(e))


def start_scheduler() -> bool:
    """Start the background pipeline and reflection loops. Returns True if started."""
    global _running, _pipeline_task, _reflection_task, _started_at, _cycles_completed

    if _running:
        return False  # already running

    _running = True
    _started_at = datetime.now(timezone.utc)
    _cycles_completed = 0
    _pipeline_task = asyncio.create_task(_pipeline_loop())
    _reflection_task = asyncio.create_task(_reflection_loop())
    log.info("scheduler_started")
    return True


async def stop_scheduler() -> bool:
    """Stop the background loops. Returns True if stopped."""
    global _running, _pipeline_task, _reflection_task, _started_at

    if not _running:
        return False  # already stopped

    _running = False
    _started_at = None
    log.info("scheduler_stopping")

    for task in (_pipeline_task, _reflection_task):
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    _pipeline_task = None
    _reflection_task = None
    log.info("scheduler_stopped")
    return True


def is_running() -> bool:
    """Check if the scheduler is currently running."""
    return _running


def get_status() -> dict:
    """Get scheduler status for the API."""
    return {
        "running": _running,
        "started_at": _started_at.isoformat() if _started_at else None,
        "cycles_completed": _cycles_completed,
    }

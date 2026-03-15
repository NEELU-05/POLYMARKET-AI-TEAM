"""Base agent class that all agents inherit from."""

import time
from abc import ABC, abstractmethod
from typing import Any

from app.core.event_bus import Event, event_bus
from app.core.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import AgentActivity


class BaseAgent(ABC):
    """Base class for all AI agents in the system."""

    name: str = "base_agent"

    def __init__(self) -> None:
        self.log = get_logger(self.name)
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        """Override in subclasses to subscribe to events."""
        pass

    async def emit(self, topic: str, data: dict) -> None:
        """Publish an event to the event bus."""
        event = Event(topic=topic, source=self.name, data=data)
        await event_bus.publish(event)

    async def log_activity(
        self, db: AsyncSession, action: str, details: dict, status: str = "completed", duration_ms: int = 0
    ) -> None:
        """Record agent activity in the database."""
        activity = AgentActivity(
            agent_name=self.name,
            action=action,
            details=details,
            status=status,
            duration_ms=duration_ms,
        )
        db.add(activity)
        await db.flush()

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's primary task."""
        raise NotImplementedError

    async def timed_run(self, db: AsyncSession, *args: Any, **kwargs: Any) -> Any:
        """Run with timing and activity logging."""
        start = time.monotonic()
        self.log.info(f"{self.name}_started")
        try:
            result = await self.run(*args, **kwargs)
            elapsed = int((time.monotonic() - start) * 1000)
            await self.log_activity(
                db, f"{self.name}_run", {"status": "success"}, "completed", elapsed
            )
            self.log.info(f"{self.name}_completed", duration_ms=elapsed)
            return result
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            await self.log_activity(
                db, f"{self.name}_run", {"error": str(e)}, "failed", elapsed
            )
            self.log.error(f"{self.name}_failed", error=str(e), duration_ms=elapsed)
            raise

"""Internal event bus for agent communication.

Simple publish-subscribe system. Agents emit events and subscribe to events
from other agents. Backed by Redis pub/sub for persistence and replay.
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from dataclasses import dataclass, field, asdict

import redis.asyncio as aioredis
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("event_bus")

EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


@dataclass
class Event:
    topic: str
    source: str
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, raw: str) -> "Event":
        return cls(**json.loads(raw))


class EventBus:
    """In-process event bus with optional Redis backing."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._redis: aioredis.Redis | None = None
        self._max_history = 500

    async def connect(self) -> None:
        settings = get_settings()
        try:
            self._redis = aioredis.from_url(
                settings.redis_url, decode_responses=True
            )
            await self._redis.ping()
            log.info("event_bus_redis_connected", url=settings.redis_url)
        except Exception as e:
            log.warning("event_bus_redis_unavailable", error=str(e))
            self._redis = None

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        self._handlers[topic].append(handler)
        log.debug("event_bus_subscribe", topic=topic, handler=handler.__qualname__)

    async def publish(self, event: Event) -> None:
        if not event.event_id:
            import uuid
            event.event_id = str(uuid.uuid4())

        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Persist to Redis stream
        if self._redis:
            try:
                await self._redis.xadd(
                    f"events:{event.topic}",
                    {"data": event.to_json()},
                    maxlen=1000,
                )
            except Exception as e:
                log.warning("event_bus_redis_publish_failed", error=str(e))

        # Dispatch to local handlers
        handlers = self._handlers.get(event.topic, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                log.error(
                    "event_bus_handler_error",
                    topic=event.topic,
                    handler=handler.__qualname__,
                    error=str(e),
                )

        log.info("event_published", topic=event.topic, source=event.source)

    def get_history(self, topic: str | None = None, limit: int = 50) -> list[dict]:
        events = self._history
        if topic:
            events = [e for e in events if e.topic == topic]
        return [e.to_dict() for e in events[-limit:]]


# Singleton
event_bus = EventBus()

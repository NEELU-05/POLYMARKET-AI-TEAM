"""Async SQLAlchemy database session management.

Uses lazy initialization to avoid reading settings at import time.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Lazy-initialized so .env is loaded before we read settings.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        from app.core.config import get_settings
        settings = get_settings()

        # SQLite doesn't use pool_size/max_overflow
        if "sqlite" in settings.database_url:
            _engine = create_async_engine(
                settings.database_url,
                echo=settings.database_echo,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_async_engine(
                settings.database_url,
                echo=settings.database_echo,
                pool_size=10,
                max_overflow=20,
            )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Public accessor used by the scheduler and pipeline triggers."""
    return _get_session_factory()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables."""
    engine = _get_engine()
    async with engine.begin() as conn:
        from app.models import db_models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None

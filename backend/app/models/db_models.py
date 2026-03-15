"""SQLAlchemy ORM models for the Polymarket AI system."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON, Enum as SAEnum
)
import enum
from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeSide(str, enum.Enum):
    YES = "yes"
    NO = "no"


class MarketRecord(Base):
    """Cached market data from Polymarket."""
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    condition_id = Column(String(256), unique=True, nullable=False, index=True)
    question = Column(Text, nullable=False)
    description = Column(Text, default="")
    category = Column(String(64), default="unknown")
    market_slug = Column(String(512), default="")
    outcome_yes_price = Column(Float, default=0.5)
    outcome_no_price = Column(Float, default=0.5)
    volume = Column(Float, default=0.0)
    liquidity = Column(Float, default=0.0)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    resolved = Column(Boolean, default=False)
    resolution_outcome = Column(String(16), nullable=True)
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Trade(Base):
    """Paper trade record."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    condition_id = Column(String(256), nullable=False, index=True)
    market_question = Column(Text, default="")
    side = Column(SAEnum(TradeSide), nullable=False)
    entry_price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    ai_probability = Column(Float, nullable=False)
    market_probability = Column(Float, nullable=False)
    edge = Column(Float, nullable=False)
    confidence = Column(Float, default=0.5)
    status = Column(SAEnum(TradeStatus), default=TradeStatus.OPEN)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    resolution_outcome = Column(String(16), nullable=True)
    entry_reasoning = Column(Text, default="")
    exit_reasoning = Column(Text, default="")
    opened_at = Column(DateTime(timezone=True), default=utcnow)
    closed_at = Column(DateTime(timezone=True), nullable=True)


class PortfolioSnapshot(Base):
    """Point-in-time portfolio state."""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    balance = Column(Float, nullable=False)
    open_positions = Column(Integer, default=0)
    total_exposure = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    roi = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), default=utcnow)


class AgentActivity(Base):
    """Log of agent actions for the dashboard."""
    __tablename__ = "agent_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(64), nullable=False, index=True)
    action = Column(String(128), nullable=False)
    details = Column(JSON, default=dict)
    status = Column(String(32), default="completed")
    duration_ms = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), default=utcnow)


class LessonLearned(Base):
    """Reflection and memory storage for the learning system."""
    __tablename__ = "lessons_learned"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, nullable=True)
    condition_id = Column(String(256), nullable=True)
    category = Column(String(64), default="general")
    mistake_type = Column(String(128), default="")
    description = Column(Text, nullable=False)
    lesson = Column(Text, nullable=False)
    confidence_before = Column(Float, nullable=True)
    confidence_after = Column(Float, nullable=True)
    severity = Column(String(32), default="medium")
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)

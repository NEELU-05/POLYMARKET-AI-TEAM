"""API routes — dashboard data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, get_async_session_factory
from app.models.db_models import (
    Trade, TradeStatus, PortfolioSnapshot, AgentActivity, LessonLearned, MarketRecord,
)
from app.trading.simulator import paper_trading
from app.services.orchestrator import orchestrator
from app.services.scheduler import start_scheduler, stop_scheduler, get_status as scheduler_status
from app.agents.portfolio_manager import portfolio_manager
from app.agents.memory_manager import memory_manager
from app.core.llm_client import llm_client
from app.core.event_bus import event_bus
from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["dashboard"])


# --- Authentication dependency ---

async def verify_api_key(authorization: str = Header(None)):
    """Verify API key from Authorization header."""
    settings = get_settings()

    # If no API_SECRET_KEY configured, allow all requests (for backward compatibility)
    if not settings.api_secret_key:
        return True

    # Require Authorization: Bearer <key>
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format. Use 'Bearer <key>'")

    token = authorization[7:]  # Strip "Bearer "

    if token != settings.api_secret_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return True


# --- Dashboard Overview ---

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Main dashboard data: balance, PnL, ROI, performance metrics."""
    metrics = await paper_trading.get_performance_metrics(db)
    balance = await paper_trading.get_balance(db)
    emergency = await paper_trading.is_emergency_mode(db)

    # Open positions count
    open_q = await db.execute(
        select(func.count(Trade.id)).where(Trade.status == TradeStatus.OPEN)
    )
    open_count = open_q.scalar() or 0

    return {
        "balance": balance,
        "currency": "₹",
        "emergency_mode": emergency,
        "open_positions": open_count,
        "metrics": metrics,
        "llm_stats": llm_client.get_stats(),
    }


@router.get("/dashboard/equity-curve")
async def get_equity_curve(db: AsyncSession = Depends(get_db)):
    """Portfolio value over time for the profit curve chart."""
    q = await db.execute(
        select(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.timestamp)
        .limit(500)
    )
    snapshots = q.scalars().all()

    return [
        {
            "timestamp": s.timestamp.isoformat(),
            "balance": s.balance,
            "pnl": s.total_pnl,
            "roi": s.roi,
        }
        for s in snapshots
    ]


# --- Trades ---

@router.get("/trades")
async def get_trades(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get trade history with optional status filter."""
    query = select(Trade).order_by(desc(Trade.opened_at))

    if status:
        try:
            ts = TradeStatus(status)
            query = query.where(Trade.status == ts)
        except ValueError:
            pass

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    trades = result.scalars().all()

    return [
        {
            "id": t.id,
            "condition_id": t.condition_id,
            "question": t.market_question,
            "side": t.side.value,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "size": t.size,
            "ai_probability": t.ai_probability,
            "market_probability": t.market_probability,
            "edge": t.edge,
            "confidence": t.confidence,
            "pnl": t.pnl,
            "status": t.status.value,
            "resolution": t.resolution_outcome,
            "reasoning": t.entry_reasoning,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


@router.get("/trades/active")
async def get_active_trades(db: AsyncSession = Depends(get_db)):
    """Get all currently open positions."""
    q = await db.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.OPEN)
        .order_by(desc(Trade.opened_at))
    )
    trades = q.scalars().all()

    total_exposure = sum(t.size for t in trades)

    return {
        "positions": [
            {
                "id": t.id,
                "condition_id": t.condition_id,
                "question": t.market_question,
                "side": t.side.value,
                "entry_price": t.entry_price,
                "size": t.size,
                "ai_probability": t.ai_probability,
                "edge": t.edge,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            }
            for t in trades
        ],
        "total_exposure": total_exposure,
        "count": len(trades),
    }


# --- Agent Activity ---

@router.get("/agents/activity")
async def get_agent_activity(
    agent_name: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get agent activity log."""
    query = select(AgentActivity).order_by(desc(AgentActivity.timestamp))

    if agent_name:
        query = query.where(AgentActivity.agent_name == agent_name)

    query = query.limit(limit)
    result = await db.execute(query)
    activities = result.scalars().all()

    return [
        {
            "id": a.id,
            "agent": a.agent_name,
            "action": a.action,
            "details": a.details,
            "status": a.status,
            "duration_ms": a.duration_ms,
            "timestamp": a.timestamp.isoformat(),
        }
        for a in activities
    ]


@router.get("/agents/status")
async def get_agent_status():
    """Get current agent status and system health."""
    agents = [
        "market_scanner", "market_classifier", "research_agent",
        "signal_agent", "probability_agent", "strategy_agent",
        "risk_manager", "execution_agent", "portfolio_manager",
        "reflection_agent", "memory_manager",
    ]
    return {
        "agents": [{"name": a, "status": "ready"} for a in agents],
        "event_bus_history": len(event_bus.get_history()),
    }


# --- Lessons / Memory ---

@router.get("/lessons")
async def get_lessons(
    category: str | None = None,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get lessons learned from past trades."""
    query = select(LessonLearned).order_by(desc(LessonLearned.created_at))

    if category:
        query = query.where(LessonLearned.category == category)

    query = query.limit(limit)
    result = await db.execute(query)
    lessons = result.scalars().all()

    return [
        {
            "id": l.id,
            "trade_id": l.trade_id,
            "category": l.category,
            "mistake_type": l.mistake_type,
            "description": l.description,
            "lesson": l.lesson,
            "severity": l.severity,
            "tags": l.tags,
            "created_at": l.created_at.isoformat(),
        }
        for l in lessons
    ]


@router.get("/memory/summary")
async def get_memory_summary(db: AsyncSession = Depends(get_db)):
    """Get aggregated memory and learning state."""
    return await memory_manager.run(db)


# --- Events ---

@router.get("/events")
async def get_events(topic: str | None = None, limit: int = 50):
    """Get recent event bus history."""
    return event_bus.get_history(topic=topic, limit=limit)


# --- Pipeline control ---

@router.post("/pipeline/run")
async def trigger_pipeline(_: bool = Depends(verify_api_key)):
    """Manually trigger one pipeline cycle."""
    factory = get_async_session_factory()
    async with factory() as db:
        report = await orchestrator.run_full_pipeline(db)
        await db.commit()
    return report


@router.post("/pipeline/reflect")
async def trigger_reflection(_: bool = Depends(verify_api_key)):
    """Manually trigger reflection cycle."""
    factory = get_async_session_factory()
    async with factory() as db:
        result = await orchestrator.run_reflection_cycle(db)
        await db.commit()
    return result


# --- System Control (Start / Stop) ---

@router.get("/system/status")
async def system_status():
    """Get system running status."""
    return scheduler_status()


@router.post("/system/start")
async def system_start(_: bool = Depends(verify_api_key)):
    """Start the AI pipeline scheduler."""
    started = start_scheduler()
    status = scheduler_status()
    if started:
        return {**status, "message": "System started"}
    return {**status, "message": "System already running"}


@router.post("/system/stop")
async def system_stop(_: bool = Depends(verify_api_key)):
    """Stop the AI pipeline scheduler."""
    stopped = await stop_scheduler()
    status = scheduler_status()
    if stopped:
        return {**status, "message": "System stopped"}
    return {**status, "message": "System already stopped"}

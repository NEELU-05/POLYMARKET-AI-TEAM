"""API routes — dashboard data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, get_async_session_factory
from app.models.db_models import (
    Trade, TradeStatus, PortfolioSnapshot, AgentActivity, LessonLearned,
)
from app.trading.simulator import paper_trading
from app.services.orchestrator import orchestrator
from app.services.scheduler import (
    start_scheduler, stop_scheduler, get_status as scheduler_status,
    is_pipeline_busy, set_pipeline_busy,
)
from app.agents.memory_manager import memory_manager
from app.core.llm_client import llm_client
from app.core.event_bus import event_bus
from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["dashboard"])

_MAX_LIMIT = 100


async def verify_api_key(authorization: str = Header(None)):
    settings = get_settings()
    if not settings.api_secret_key:
        return True
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    if authorization[7:] != settings.api_secret_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    metrics = await paper_trading.get_performance_metrics(db)
    balance = await paper_trading.get_balance(db)
    emergency = await paper_trading.is_emergency_mode(db)

    open_q = await db.execute(
        select(func.count(Trade.id)).where(Trade.status == TradeStatus.OPEN)
    )
    open_count = open_q.scalar() or 0

    llm_stats = llm_client.get_stats()

    return {
        "balance": balance,
        "currency": "₹",
        "emergency_mode": emergency,
        "open_positions": open_count,
        "metrics": metrics,
        "llm_stats": llm_stats,
    }


@router.get("/dashboard/equity-curve")
async def get_equity_curve(db: AsyncSession = Depends(get_db)):
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


@router.get("/trades")
async def get_trades(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    limit = min(limit, _MAX_LIMIT)
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
    q = await db.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.OPEN)
        .order_by(desc(Trade.opened_at))
    )
    trades = q.scalars().all()
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
        "total_exposure": sum(t.size for t in trades),
        "count": len(trades),
    }


@router.get("/agents/activity")
async def get_agent_activity(
    agent_name: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    limit = min(limit, _MAX_LIMIT)
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


@router.get("/lessons")
async def get_lessons(
    category: str | None = None,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(limit, _MAX_LIMIT)
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
    return await memory_manager.run(db)


@router.get("/events")
async def get_events(topic: str | None = None, limit: int = 50):
    return event_bus.get_history(topic=topic, limit=min(limit, _MAX_LIMIT))


# --- Pipeline analytics endpoint (for real chart data) ---

@router.get("/analytics/trades-summary")
async def get_trades_summary(db: AsyncSession = Depends(get_db)):
    """Returns aggregated trade data for dashboard charts."""
    closed_q = await db.execute(
        select(Trade).where(Trade.status == TradeStatus.CLOSED)
    )
    closed = closed_q.scalars().all()

    # Edge distribution buckets
    edge_buckets: dict[str, dict] = {
        "0-5%": {"wins": 0, "losses": 0},
        "5-10%": {"wins": 0, "losses": 0},
        "10-15%": {"wins": 0, "losses": 0},
        "15-20%": {"wins": 0, "losses": 0},
        "20%+": {"wins": 0, "losses": 0},
    }
    for t in closed:
        e = t.edge * 100
        bucket = "20%+" if e >= 20 else f"{int(e // 5) * 5}-{int(e // 5) * 5 + 5}%"
        if bucket not in edge_buckets:
            bucket = "20%+"
        key = "wins" if (t.pnl or 0) > 0 else "losses"
        edge_buckets[bucket][key] += 1

    # Daily PnL (from portfolio snapshots)
    snaps_q = await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp).limit(500)
    )
    snaps = snaps_q.scalars().all()
    daily_pnl: dict[str, float] = {}
    for s in snaps:
        day = s.timestamp.strftime("%Y-%m-%d")
        daily_pnl[day] = s.total_pnl  # last snapshot of day wins

    return {
        "edge_distribution": [
            {"name": k, "wins": v["wins"], "losses": v["losses"]}
            for k, v in edge_buckets.items()
        ],
        "daily_pnl": [
            {"date": d, "pnl": p} for d, p in sorted(daily_pnl.items())
        ],
        "total_closed": len(closed),
    }


# --- Pipeline control ---

@router.post("/pipeline/run")
async def trigger_pipeline(_: bool = Depends(verify_api_key)):
    """Manually trigger one pipeline cycle. Returns 409 if already running."""
    if is_pipeline_busy():
        raise HTTPException(status_code=409, detail="Pipeline already running")
    set_pipeline_busy(True)
    try:
        factory = get_async_session_factory()
        async with factory() as db:
            report = await orchestrator.run_full_pipeline(db)
            await db.commit()
    finally:
        set_pipeline_busy(False)
    return report


@router.post("/pipeline/reflect")
async def trigger_reflection(_: bool = Depends(verify_api_key)):
    factory = get_async_session_factory()
    async with factory() as db:
        result = await orchestrator.run_reflection_cycle(db)
        await db.commit()
    return result


@router.get("/system/status")
async def system_status():
    return scheduler_status()


@router.post("/system/start")
async def system_start(_: bool = Depends(verify_api_key)):
    started = start_scheduler()
    status = scheduler_status()
    return {**status, "message": "System started" if started else "System already running"}


@router.post("/system/stop")
async def system_stop(_: bool = Depends(verify_api_key)):
    stopped = await stop_scheduler()
    status = scheduler_status()
    return {**status, "message": "System stopped" if stopped else "System already stopped"}

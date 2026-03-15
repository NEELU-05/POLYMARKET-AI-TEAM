"""Portfolio Manager Agent — tracks positions, balance, and performance metrics."""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.models.schemas import PortfolioState
from app.models.db_models import Trade, TradeStatus, PortfolioSnapshot


class PortfolioManagerAgent(BaseAgent):
    name = "portfolio_manager"

    async def run(self, db: AsyncSession) -> PortfolioState:
        """Calculate current portfolio state from trade history."""
        settings = get_settings()

        # Count trades
        total_trades_q = await db.execute(select(func.count(Trade.id)))
        total_trades = total_trades_q.scalar() or 0

        # Open positions
        open_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = open_q.scalars().all()
        open_positions = len(open_trades)

        # Total exposure
        total_exposure = sum(t.size for t in open_trades)

        # Closed trades for PnL
        closed_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.CLOSED)
        )
        closed_trades = closed_q.scalars().all()

        total_pnl = sum(t.pnl or 0 for t in closed_trades)
        win_count = sum(1 for t in closed_trades if (t.pnl or 0) > 0)
        loss_count = sum(1 for t in closed_trades if (t.pnl or 0) <= 0)
        win_rate = win_count / max(len(closed_trades), 1)

        # Balance
        balance = settings.starting_capital + total_pnl - total_exposure

        # ROI
        roi = total_pnl / settings.starting_capital if settings.starting_capital > 0 else 0

        # Drawdown calculation
        max_drawdown = self._calculate_drawdown(closed_trades, settings.starting_capital)

        state = PortfolioState(
            balance=round(balance, 2),
            open_positions=open_positions,
            total_exposure=round(total_exposure, 2),
            total_pnl=round(total_pnl, 2),
            total_trades=total_trades,
            win_rate=round(win_rate, 4),
            roi=round(roi, 4),
            max_drawdown=round(max_drawdown, 4),
        )

        # Save snapshot
        snapshot = PortfolioSnapshot(
            balance=state.balance,
            open_positions=state.open_positions,
            total_exposure=state.total_exposure,
            total_pnl=state.total_pnl,
            total_trades=state.total_trades,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=state.win_rate,
            roi=state.roi,
            max_drawdown=state.max_drawdown,
        )
        db.add(snapshot)

        await self.emit("portfolio_updated", state.model_dump())

        return state

    def _calculate_drawdown(self, closed_trades: list[Trade], starting: float) -> float:
        """Calculate maximum drawdown from trade history."""
        if not closed_trades:
            return 0.0

        sorted_trades = sorted(closed_trades, key=lambda t: t.closed_at or t.opened_at)
        equity = starting
        peak = starting
        max_dd = 0.0

        for trade in sorted_trades:
            equity += trade.pnl or 0
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)

        return max_dd


portfolio_manager = PortfolioManagerAgent()

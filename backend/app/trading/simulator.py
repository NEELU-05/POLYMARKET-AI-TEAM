"""Paper Trading Simulator — manages the simulated wallet and trade lifecycle."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.db_models import Trade, TradeStatus, PortfolioSnapshot

log = get_logger("paper_trading")


class PaperTradingSimulator:
    """Simulates trade execution and PnL tracking without real money."""

    def __init__(self) -> None:
        self._settings = None

    @property
    def settings(self):
        if self._settings is None:
            from app.core.config import get_settings
            self._settings = get_settings()
        return self._settings

    async def get_balance(self, db: AsyncSession) -> float:
        """Calculate current balance from trade history."""
        # Get latest snapshot or compute from scratch
        snapshot_q = await db.execute(
            select(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.timestamp.desc())
            .limit(1)
        )
        snapshot = snapshot_q.scalar_one_or_none()

        if snapshot:
            return snapshot.balance

        return await self._compute_balance(db)

    async def _compute_balance(self, db: AsyncSession) -> float:
        """Compute balance from trade history."""
        starting = self.settings.starting_capital

        # Sum closed PnL
        closed_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.CLOSED)
        )
        closed = closed_q.scalars().all()
        closed_pnl = sum(t.pnl or 0 for t in closed)

        # Subtract open exposure
        open_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = open_q.scalars().all()
        open_exposure = sum(t.size for t in open_trades)

        return starting + closed_pnl - open_exposure

    async def can_trade(self, db: AsyncSession) -> tuple[bool, str]:
        """Check if trading is allowed under survival protocol."""
        balance = await self.get_balance(db)

        if balance <= self.settings.stop_balance:
            return False, f"Balance {self.settings.currency_symbol}{balance:.2f} below stop level"

        # Count open positions
        open_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_count = len(open_q.scalars().all())

        if open_count >= self.settings.max_open_trades:
            return False, f"Max open trades ({self.settings.max_open_trades}) reached"

        return True, "OK"

    async def is_emergency_mode(self, db: AsyncSession) -> bool:
        """Check if balance is in emergency zone."""
        balance = await self.get_balance(db)
        return balance <= self.settings.emergency_balance

    async def close_trade(
        self, db: AsyncSession, trade_id: int, winning_outcome: str
    ) -> Trade | None:
        """Close a trade based on market resolution."""
        trade_q = await db.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        trade = trade_q.scalar_one_or_none()

        if not trade or trade.status != TradeStatus.OPEN:
            return None

        trade_side = trade.side.value

        if trade_side == winning_outcome:
            payout = trade.size / trade.entry_price
            trade.pnl = payout - trade.size
            trade.exit_price = 1.0
        else:
            trade.pnl = -trade.size
            trade.exit_price = 0.0

        trade.status = TradeStatus.CLOSED
        trade.resolution_outcome = winning_outcome
        trade.closed_at = datetime.now(timezone.utc)

        log.info(
            "trade_closed",
            trade_id=trade.id,
            side=trade_side,
            outcome=winning_outcome,
            pnl=trade.pnl,
        )

        return trade

    async def get_performance_metrics(self, db: AsyncSession) -> dict:
        """Calculate comprehensive performance metrics."""
        closed_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.CLOSED)
        )
        closed = closed_q.scalars().all()

        if not closed:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "roi": 0,
                "avg_edge": 0,
                "prediction_accuracy": 0,
                "calibration_error": 0,
                "max_drawdown": 0,
            }

        wins = [t for t in closed if (t.pnl or 0) > 0]
        total_pnl = sum(t.pnl or 0 for t in closed)

        # Prediction accuracy: how often AI's side was correct
        correct = sum(
            1 for t in closed
            if t.resolution_outcome == t.side.value
        )

        # Calibration error: average |predicted_prob - actual_outcome|
        cal_errors = []
        for t in closed:
            actual = 1.0 if t.resolution_outcome == "yes" else 0.0
            cal_errors.append(abs(t.ai_probability - actual))

        # Drawdown
        equity = self.settings.starting_capital
        peak = equity
        max_dd = 0.0
        sorted_trades = sorted(closed, key=lambda t: t.closed_at or t.opened_at)
        for t in sorted_trades:
            equity += t.pnl or 0
            peak = max(peak, equity)
            dd = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            "total_trades": len(closed),
            "win_rate": round(len(wins) / len(closed), 4),
            "total_pnl": round(total_pnl, 2),
            "roi": round(total_pnl / self.settings.starting_capital, 4),
            "avg_edge": round(sum(t.edge for t in closed) / len(closed), 4),
            "prediction_accuracy": round(correct / len(closed), 4),
            "calibration_error": round(sum(cal_errors) / len(cal_errors), 4),
            "max_drawdown": round(max_dd, 4),
        }


# Singleton
paper_trading = PaperTradingSimulator()

"""Risk Manager Agent — applies capital protection rules before trade execution."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.models.db_models import Trade, TradeStatus
from app.models.schemas import TradeOpportunity, RiskAssessment, PortfolioState


class RiskManagerAgent(BaseAgent):
    name = "risk_manager"

    async def run(
        self,
        opportunity: TradeOpportunity,
        portfolio: PortfolioState,
        db: AsyncSession | None = None,
    ) -> RiskAssessment:
        """Evaluate a trade opportunity against risk constraints."""
        settings = get_settings()
        warnings: list[str] = []
        adjusted_size = opportunity.suggested_size

        # Check: Stop trading if balance too low
        if portfolio.balance <= settings.stop_balance:
            return self._reject(
                opportunity, 0, 1.0, warnings,
                f"Balance ₹{portfolio.balance:.2f} below stop threshold ₹{settings.stop_balance:.2f}",
            )

        # Check: Duplicate position (if db provided)
        if db is not None:
            dup_q = await db.execute(
                select(Trade).where(
                    Trade.condition_id == opportunity.condition_id,
                    Trade.status == TradeStatus.OPEN,
                )
            )
            if dup_q.scalar_one_or_none():
                return self._reject(
                    opportunity, 0, 0.5, warnings,
                    f"Already have an open position on {opportunity.condition_id[:20]}",
                )

        # Emergency mode — reduce position size
        if portfolio.balance <= settings.emergency_balance:
            warnings.append("EMERGENCY MODE: Balance below emergency threshold")
            adjusted_size = min(adjusted_size, 10.0)

        # Max open trades
        if portfolio.open_positions >= settings.max_open_trades:
            return self._reject(
                opportunity, 0, 0.8, warnings,
                f"Max open trades ({settings.max_open_trades}) reached",
            )

        # Cap to max trade size
        if adjusted_size > settings.max_trade_size:
            adjusted_size = settings.max_trade_size
            warnings.append(f"Size capped to max ₹{settings.max_trade_size}")

        # Afford check
        if adjusted_size > portfolio.balance:
            adjusted_size = portfolio.balance * 0.5
            warnings.append("Size reduced: insufficient balance")

        # Drawdown circuit breaker
        if portfolio.max_drawdown > 0.25:
            return self._reject(
                opportunity, 0, 1.0, warnings,
                f"Drawdown {portfolio.max_drawdown:.1%} exceeds 25% circuit breaker",
            )

        # Don't force a minimum — if Kelly says a tiny bet, respect it.
        # Drop trades that would be < ₹1 (genuinely not worth the spread cost).
        if adjusted_size < 1.0:
            return self._reject(
                opportunity, 0, 0.3, warnings,
                f"Kelly-sized trade too small (₹{adjusted_size:.2f} < ₹1 minimum)",
            )

        risk_score = self._calculate_risk_score(opportunity, portfolio)
        if risk_score > 0.85:
            return self._reject(opportunity, 0, risk_score, warnings,
                                f"Risk score too high: {risk_score:.2f}")

        assessment = RiskAssessment(
            approved=True,
            trade=opportunity,
            adjusted_size=round(adjusted_size, 2),
            risk_score=round(risk_score, 3),
            warnings=warnings,
            rejection_reason="",
        )
        self.log.info(
            "risk_assessment_approved",
            condition_id=opportunity.condition_id,
            risk_score=risk_score,
            size=adjusted_size,
        )
        return assessment

    def _reject(
        self,
        trade: TradeOpportunity,
        size: float,
        risk_score: float,
        warnings: list[str],
        reason: str,
    ) -> RiskAssessment:
        self.log.info("risk_assessment_rejected", condition_id=trade.condition_id, reason=reason)
        return RiskAssessment(
            approved=False,
            trade=trade,
            adjusted_size=size,
            risk_score=round(risk_score, 3),
            warnings=warnings,
            rejection_reason=reason,
        )

    def _calculate_risk_score(
        self, opp: TradeOpportunity, portfolio: PortfolioState
    ) -> float:
        scores = []
        if portfolio.open_positions > 0:
            concentration = opp.suggested_size / max(portfolio.balance, 1)
            scores.append(concentration)
        scores.append(1.0 - opp.confidence)
        scores.append(max(0, 1.0 - (opp.edge * 5)))
        scores.append(portfolio.max_drawdown * 2)
        return min(1.0, sum(scores) / max(len(scores), 1))


risk_manager = RiskManagerAgent()

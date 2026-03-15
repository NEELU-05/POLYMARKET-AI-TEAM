"""Risk Manager Agent — applies capital protection rules before trade execution."""

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.models.schemas import TradeOpportunity, RiskAssessment, PortfolioState


class RiskManagerAgent(BaseAgent):
    name = "risk_manager"

    async def run(
        self, opportunity: TradeOpportunity, portfolio: PortfolioState
    ) -> RiskAssessment:
        """Evaluate a trade opportunity against risk constraints."""
        settings = get_settings()
        warnings: list[str] = []
        approved = True
        rejection_reason = ""
        adjusted_size = opportunity.suggested_size

        # Check: Stop trading if balance too low
        if portfolio.balance <= settings.stop_balance:
            approved = False
            rejection_reason = (
                f"Balance {settings.currency_symbol}{portfolio.balance:.2f} "
                f"below stop threshold {settings.currency_symbol}{settings.stop_balance:.2f}"
            )
            return self._build_assessment(
                False, opportunity, 0, 1.0, warnings, rejection_reason
            )

        # Check: Emergency mode — reduce position size
        if portfolio.balance <= settings.emergency_balance:
            warnings.append("EMERGENCY MODE: Balance below emergency threshold")
            adjusted_size = min(adjusted_size, 10.0)

        # Check: Max open trades
        if portfolio.open_positions >= settings.max_open_trades:
            approved = False
            rejection_reason = (
                f"Max open trades ({settings.max_open_trades}) reached"
            )
            return self._build_assessment(
                False, opportunity, 0, 0.8, warnings, rejection_reason
            )

        # Check: Max trade size
        if adjusted_size > settings.max_trade_size:
            adjusted_size = settings.max_trade_size
            warnings.append(f"Size capped to max {settings.currency_symbol}{settings.max_trade_size}")

        # Check: Can afford trade
        if adjusted_size > portfolio.balance:
            adjusted_size = portfolio.balance * 0.5
            warnings.append("Size reduced: insufficient balance")

        # Check: Max drawdown circuit breaker (25%)
        if portfolio.max_drawdown > 0.25:
            approved = False
            rejection_reason = (
                f"Drawdown {portfolio.max_drawdown:.1%} exceeds 25% circuit breaker"
            )
            return self._build_assessment(
                False, opportunity, 0, 1.0, warnings, rejection_reason
            )

        # Risk score (lower is better)
        risk_score = self._calculate_risk_score(opportunity, portfolio)

        if risk_score > 0.85:
            approved = False
            rejection_reason = f"Risk score too high: {risk_score:.2f}"

        return self._build_assessment(
            approved, opportunity, adjusted_size, risk_score, warnings, rejection_reason
        )

    def _calculate_risk_score(
        self, opp: TradeOpportunity, portfolio: PortfolioState
    ) -> float:
        """Calculate composite risk score 0-1 (lower = safer)."""
        scores = []

        # Concentration risk
        if portfolio.open_positions > 0:
            concentration = opp.suggested_size / max(portfolio.balance, 1)
            scores.append(concentration)

        # Confidence risk (inverse)
        scores.append(1.0 - opp.confidence)

        # Edge risk (lower edge = higher risk)
        scores.append(max(0, 1.0 - (opp.edge * 5)))

        # Drawdown risk
        scores.append(portfolio.max_drawdown * 2)

        return min(1.0, sum(scores) / max(len(scores), 1))

    def _build_assessment(
        self,
        approved: bool,
        trade: TradeOpportunity,
        adjusted_size: float,
        risk_score: float,
        warnings: list[str],
        rejection_reason: str,
    ) -> RiskAssessment:
        assessment = RiskAssessment(
            approved=approved,
            trade=trade,
            adjusted_size=round(adjusted_size, 2),
            risk_score=round(risk_score, 3),
            warnings=warnings,
            rejection_reason=rejection_reason,
        )

        status = "approved" if approved else "rejected"
        self.log.info(
            f"risk_assessment_{status}",
            condition_id=trade.condition_id,
            risk_score=risk_score,
            size=adjusted_size,
        )

        return assessment


risk_manager = RiskManagerAgent()

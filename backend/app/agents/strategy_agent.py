"""Strategy Agent — detects trading opportunities based on probability edge + resolution timing."""

from datetime import datetime, timezone

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.models.schemas import ProbabilityEstimate, TradeOpportunity, MarketData


class StrategyAgent(BaseAgent):
    name = "strategy_agent"

    async def run(
        self,
        estimates: list[ProbabilityEstimate],
        current_balance: float | None = None,
        markets: list[MarketData] | None = None,
    ) -> list[TradeOpportunity]:
        """Identify trading opportunities where AI probability diverges from market.

        Also applies resolution timing strategy for near-expiry obvious outcomes.
        """
        settings = get_settings()
        opportunities = []
        bankroll = current_balance if current_balance is not None else settings.starting_capital

        # Build market lookup for resolution timing
        market_map = {}
        if markets:
            market_map = {m.condition_id: m for m in markets}

        for est in estimates:
            if est.edge < settings.min_edge:
                self.log.debug("edge_too_small", condition_id=est.condition_id, edge=est.edge)
                continue

            if est.confidence < 0.1:
                self.log.debug("confidence_too_low", condition_id=est.condition_id, confidence=est.confidence)
                continue

            # Determine side
            if est.ai_probability > est.market_probability:
                side = "yes"
                entry_price = est.market_probability
            else:
                side = "no"
                entry_price = 1.0 - est.market_probability

            # Check for resolution timing opportunity
            market = market_map.get(est.condition_id)
            resolution_bonus = self._check_resolution_timing(market, est)

            # Kelly criterion sizing (quarter-Kelly for safety)
            odds = (1.0 / entry_price) - 1.0 if entry_price > 0 else 0
            win_prob = est.ai_probability if side == "yes" else (1.0 - est.ai_probability)
            kelly_fraction = ((win_prob * odds) - (1.0 - win_prob)) / odds if odds > 0 else 0
            quarter_kelly = max(0, kelly_fraction * 0.25)

            suggested_size = min(settings.max_trade_size, bankroll * quarter_kelly)

            # Resolution timing: 2x size for near-certain near-expiry bets
            if resolution_bonus:
                suggested_size = min(settings.max_trade_size, suggested_size * 2.0)

            if suggested_size < 3.0:
                suggested_size = 3.0

            reasoning = est.reasoning
            if resolution_bonus:
                reasoning = f"[RESOLUTION TIMING] {resolution_bonus} | {reasoning}"

            opp = TradeOpportunity(
                condition_id=est.condition_id,
                question=est.question,
                side=side,
                ai_probability=est.ai_probability,
                market_probability=est.market_probability,
                edge=est.edge,
                suggested_size=round(suggested_size, 2),
                confidence=est.confidence,
                reasoning=reasoning,
            )
            opportunities.append(opp)

        # Sort: resolution timing trades first, then by edge * confidence
        opportunities.sort(
            key=lambda x: (
                1 if "[RESOLUTION TIMING]" in x.reasoning else 0,
                x.edge * x.confidence,
            ),
            reverse=True,
        )

        self.log.info(
            "opportunities_found",
            count=len(opportunities),
            top_edge=opportunities[0].edge if opportunities else 0,
            resolution_timing=sum(1 for o in opportunities if "[RESOLUTION TIMING]" in o.reasoning),
        )

        await self.emit("opportunities_identified", {
            "count": len(opportunities),
            "opportunities": [o.model_dump() for o in opportunities[:5]],
        })

        return opportunities

    def _check_resolution_timing(
        self, market: MarketData | None, est: ProbabilityEstimate
    ) -> str:
        """Check if a market qualifies for resolution timing strategy.

        Criteria:
        - Market ends within 48 hours
        - Outcome is nearly certain (price > 0.92 or < 0.08)
        - AI confidence is high (>0.7)

        Returns reasoning string if qualifies, empty string if not.
        """
        if not market or not market.end_date:
            return ""

        now = datetime.now(timezone.utc)
        end = market.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        hours_remaining = (end - now).total_seconds() / 3600

        if hours_remaining <= 0 or hours_remaining > 48:
            return ""

        yes_price = market.outcome_yes_price
        is_near_certain = yes_price > 0.92 or yes_price < 0.08

        if not is_near_certain:
            return ""

        if est.confidence < 0.7:
            return ""

        expected_return = (1.0 - yes_price) if yes_price > 0.92 else yes_price
        return (
            f"Near-expiry ({hours_remaining:.0f}h left), "
            f"outcome near-certain (YES={yes_price:.0%}), "
            f"expected return ~{expected_return:.0%}"
        )


strategy_agent = StrategyAgent()

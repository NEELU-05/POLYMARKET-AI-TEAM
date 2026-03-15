"""Execution Agent — executes simulated trades with orderbook-aware pricing."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.models.schemas import RiskAssessment, TradeExecution
from app.models.db_models import Trade, TradeStatus, TradeSide
from app.services.polymarket import polymarket_service


def _analyze_orderbook(book: dict, side: str, trade_size: float) -> dict:
    """Analyze orderbook to get real fill price and spread.

    Args:
        book: {"bids": [...], "asks": [...]} from CLOB API
        side: "yes" or "no"
        trade_size: intended trade size in dollars

    Returns:
        Dict with spread, fill_price, sufficient_liquidity
    """
    bids = book.get("bids", [])
    asks = book.get("asks", [])

    if not bids or not asks:
        return {"has_book": False}

    try:
        # Best bid/ask
        best_bid = float(bids[0].get("price", 0))
        best_ask = float(asks[0].get("price", 1))
        spread = best_ask - best_bid
        midpoint = (best_bid + best_ask) / 2

        # Estimate fill price by walking the book
        # Buying YES = hitting asks; Buying NO = hitting bids (inverted)
        if side == "yes":
            levels = asks  # we buy from the ask side
        else:
            levels = bids  # for NO, we buy from bid side (inverted market)

        remaining = trade_size
        total_cost = 0.0
        total_shares = 0.0

        for level in levels:
            price = float(level.get("price", 0))
            size = float(level.get("size", 0))
            level_value = price * size  # dollar value at this level

            if remaining <= 0:
                break

            fill_at_level = min(remaining, level_value)
            shares_at_level = fill_at_level / price if price > 0 else 0
            total_cost += fill_at_level
            total_shares += shares_at_level
            remaining -= fill_at_level

        fill_price = total_cost / total_shares if total_shares > 0 else midpoint
        sufficient_liquidity = remaining <= 0

        return {
            "has_book": True,
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "spread": round(spread, 4),
            "midpoint": round(midpoint, 4),
            "fill_price": round(fill_price, 4),
            "sufficient_liquidity": sufficient_liquidity,
            "unfilled": round(remaining, 2),
        }

    except (ValueError, TypeError, IndexError):
        return {"has_book": False}


class ExecutionAgent(BaseAgent):
    name = "execution_agent"

    MAX_SPREAD = 0.08  # Skip trades with spread > 8 cents

    async def run(
        self, assessment: RiskAssessment, db: AsyncSession
    ) -> TradeExecution | None:
        """Execute a paper trade if risk assessment is approved."""
        if not assessment.approved:
            self.log.info(
                "trade_rejected",
                reason=assessment.rejection_reason,
                condition_id=assessment.trade.condition_id,
            )
            return None

        opp = assessment.trade

        # Fetch orderbook for smart entry pricing
        # We need the token_id but TradeOpportunity doesn't have it,
        # so we look it up from the market
        market = await polymarket_service.fetch_market_by_id(opp.condition_id)
        book_analysis = {"has_book": False}

        if market and market.token_id:
            book = await polymarket_service.fetch_orderbook(market.token_id)
            book_analysis = _analyze_orderbook(book, opp.side, assessment.adjusted_size)

        # Check spread — skip if too wide
        if book_analysis.get("has_book") and book_analysis.get("spread", 0) > self.MAX_SPREAD:
            self.log.warning(
                "trade_skipped_wide_spread",
                condition_id=opp.condition_id,
                spread=book_analysis["spread"],
            )
            return None

        # Determine entry price: use real fill price if available, else market price
        if book_analysis.get("has_book") and book_analysis.get("fill_price"):
            entry_price = book_analysis["fill_price"]
        else:
            entry_price = (
                opp.market_probability if opp.side == "yes"
                else 1.0 - opp.market_probability
            )

        trade = Trade(
            condition_id=opp.condition_id,
            market_question=opp.question,
            side=TradeSide.YES if opp.side == "yes" else TradeSide.NO,
            entry_price=entry_price,
            size=assessment.adjusted_size,
            ai_probability=opp.ai_probability,
            market_probability=opp.market_probability,
            edge=opp.edge,
            confidence=opp.confidence,
            status=TradeStatus.OPEN,
            entry_reasoning=opp.reasoning[:500],
        )

        db.add(trade)
        await db.flush()
        await db.refresh(trade)

        self.log.info(
            "trade_executed",
            trade_id=trade.id,
            condition_id=opp.condition_id,
            side=opp.side,
            size=assessment.adjusted_size,
            entry_price=entry_price,
            spread=book_analysis.get("spread", "N/A"),
        )

        await self.emit("trade_executed", {
            "trade_id": trade.id,
            "condition_id": opp.condition_id,
            "side": opp.side,
            "size": assessment.adjusted_size,
            "entry_price": entry_price,
        })

        return TradeExecution(
            trade_id=trade.id,
            condition_id=opp.condition_id,
            side=opp.side,
            entry_price=entry_price,
            size=assessment.adjusted_size,
            status="open",
            timestamp=datetime.now(timezone.utc),
        )


execution_agent = ExecutionAgent()

"""Signal Agent — generates structured trading signals from research + real market data."""

from app.agents.base import BaseAgent
from app.core.llm_client import llm_client
from app.models.schemas import MarketData, ResearchResult, Signal
from app.services.polymarket import polymarket_service


SYSTEM_PROMPT = """You are a trading signal generator for prediction markets. Given market data,
real price history, and research, extract structured trading signals.

Analyze these dimensions:
- Sentiment: public/media sentiment direction
- Momentum: is the market price trending in one direction? USE THE REAL PRICE DATA PROVIDED.
- Fundamental: what do the facts suggest?
- Macro: broader economic/political factors
- Risk: key risks that could invalidate the thesis

Respond with JSON:
{
  "direction": "yes" or "no",
  "strength": <0.0-1.0>,
  "signal_type": "composite",
  "reasoning": "<brief explanation>",
  "factors": {
    "sentiment": {"direction": "yes/no", "strength": <0-1>},
    "momentum": {"direction": "yes/no", "strength": <0-1>},
    "fundamental": {"direction": "yes/no", "strength": <0-1>},
    "macro": {"direction": "yes/no", "strength": <0-1>},
    "risk_level": <0-1>
  }
}"""


def _compute_momentum(timeseries: list[dict], current_price: float) -> dict:
    """Compute real momentum metrics from price timeseries."""
    if not timeseries or len(timeseries) < 2:
        return {}

    prices = []
    for point in timeseries:
        try:
            p = float(point.get("p", point.get("price", 0)))
            if p > 0:
                prices.append(p)
        except (ValueError, TypeError):
            continue

    if len(prices) < 2:
        return {}

    latest = prices[-1] if prices else current_price
    result = {"latest_price": latest, "data_points": len(prices)}

    lookbacks = {
        "1h": min(1, len(prices) - 1),
        "6h": min(6, len(prices) - 1),
        "24h": min(24, len(prices) - 1),
        "7d": min(168, len(prices) - 1),
    }

    for label, idx in lookbacks.items():
        if idx > 0 and idx < len(prices):
            old_price = prices[-(idx + 1)]
            if old_price > 0:
                change = (latest - old_price) / old_price
                result[f"change_{label}"] = round(change, 4)
                result[f"price_{label}_ago"] = round(old_price, 4)

    if "change_24h" in result:
        result["trend"] = "up" if result["change_24h"] > 0.01 else (
            "down" if result["change_24h"] < -0.01 else "flat"
        )

    return result


def _detect_volume_spike(trades: list[dict]) -> dict:
    """Detect unusual volume from recent trades.

    Returns spike data: avg size, recent size, spike ratio.
    """
    if not trades or len(trades) < 5:
        return {}

    sizes = []
    for t in trades:
        try:
            size = float(t.get("size", t.get("amount", 0)))
            if size > 0:
                sizes.append(size)
        except (ValueError, TypeError):
            continue

    if len(sizes) < 5:
        return {}

    avg_size = sum(sizes) / len(sizes)
    recent_5 = sizes[:5]  # most recent trades
    recent_avg = sum(recent_5) / len(recent_5)

    spike_ratio = recent_avg / avg_size if avg_size > 0 else 1.0

    return {
        "avg_trade_size": round(avg_size, 2),
        "recent_avg_size": round(recent_avg, 2),
        "spike_ratio": round(spike_ratio, 2),
        "is_spike": spike_ratio > 2.0,
        "trade_count": len(sizes),
    }


class SignalAgent(BaseAgent):
    name = "signal_agent"

    async def run(self, market: MarketData, research: ResearchResult) -> Signal:
        """Generate trading signals from market data, real price history, and research."""
        # Fetch real price timeseries if token_id is available
        momentum = {}
        volume_spike = {}

        if market.token_id:
            timeseries = await polymarket_service.fetch_market_timeseries(
                market.token_id, fidelity=60
            )
            momentum = _compute_momentum(timeseries, market.outcome_yes_price)

        # Fetch recent trades for volume spike detection
        trades = await polymarket_service.fetch_market_trades(
            market.condition_id, limit=50
        )
        volume_spike = _detect_volume_spike(trades)

        # Build momentum text for the LLM
        momentum_text = ""
        if momentum:
            momentum_text = "\nReal Price Momentum Data:\n"
            if "change_1h" in momentum:
                momentum_text += f"  1h change: {momentum['change_1h']:+.2%}\n"
            if "change_6h" in momentum:
                momentum_text += f"  6h change: {momentum['change_6h']:+.2%}\n"
            if "change_24h" in momentum:
                momentum_text += f"  24h change: {momentum['change_24h']:+.2%}\n"
            if "change_7d" in momentum:
                momentum_text += f"  7d change: {momentum['change_7d']:+.2%}\n"
            if "trend" in momentum:
                momentum_text += f"  Overall trend: {momentum['trend']}\n"
        else:
            momentum_text = "\nNo price history available — estimate momentum from context.\n"

        # Build volume spike text
        spike_text = ""
        if volume_spike:
            spike_text = "\nVolume Activity:\n"
            spike_text += f"  Avg trade size: ${volume_spike['avg_trade_size']:.2f}\n"
            spike_text += f"  Recent avg size: ${volume_spike['recent_avg_size']:.2f}\n"
            spike_text += f"  Spike ratio: {volume_spike['spike_ratio']:.1f}x\n"
            if volume_spike["is_spike"]:
                spike_text += "  *** VOLUME SPIKE DETECTED — smart money may be moving ***\n"

        user_prompt = (
            f"Market: {market.question}\n"
            f"Description: {market.description[:500]}\n"
            f"Current YES price: {market.outcome_yes_price:.2f}\n"
            f"Volume: ${market.volume:,.0f}\n"
            f"{momentum_text}{spike_text}\n"
            f"Research Summary: {research.summary}\n"
            f"Key Factors: {', '.join(research.key_factors[:5])}\n"
            f"Research Confidence: {research.confidence:.2f}"
        )

        result = await llm_client.query(SYSTEM_PROMPT, user_prompt)

        if result.get("parse_error"):
            return Signal(
                condition_id=market.condition_id,
                signal_type="error",
                direction="yes",
                strength=0.0,
                reasoning="Signal generation failed",
            )

        signal = Signal(
            condition_id=market.condition_id,
            signal_type=result.get("signal_type", "composite"),
            direction=result.get("direction", "yes"),
            strength=float(result.get("strength", 0.5)),
            reasoning=result.get("reasoning", ""),
            factors=result.get("factors", {}),
        )

        await self.emit("signal_generated", {
            "condition_id": market.condition_id,
            "direction": signal.direction,
            "strength": signal.strength,
        })

        return signal


signal_agent = SignalAgent()

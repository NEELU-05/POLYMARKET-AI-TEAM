"""Probability Agent — estimates real-world probability of market outcomes."""

from app.agents.base import BaseAgent
from app.core.llm_client import llm_client
from app.models.schemas import MarketData, ResearchResult, Signal, ProbabilityEstimate


SYSTEM_PROMPT = """You are a calibrated probability estimator for prediction markets. Your job is to
estimate the TRUE probability that an event occurs, independent of the market price.

Rules:
- Be well-calibrated: when you say 70%, the event should happen ~70% of the time
- Do not anchor to the market price — form your own view
- Account for base rates and reference classes
- Express genuine uncertainty — avoid overconfidence

Given market data, research, and signals, produce your probability estimate.

Respond with JSON:
{
  "ai_probability": <0.0-1.0 your estimate of true probability>,
  "confidence": <0.0-1.0 how confident you are in your estimate>,
  "reasoning": "<step-by-step reasoning>",
  "key_assumptions": ["<assumption1>", "<assumption2>"],
  "base_rate": <0.0-1.0 historical base rate if applicable>,
  "adjustment_factors": ["<why you adjusted from base rate>"]
}"""


def _format_calibration(calibration: dict) -> str:
    """Format calibration history into a prompt section."""
    if not calibration:
        return ""

    text = "\nYOUR CALIBRATION HISTORY (adjust your estimates accordingly):\n"

    if "overall" in calibration:
        o = calibration["overall"]
        text += f"  Overall: avg error {o.get('avg_error', 0):.0%}, "
        text += f"bias {o.get('bias', 'none')}\n"

    if "by_category" in calibration:
        for cat, stats in calibration["by_category"].items():
            text += f"  {cat}: win rate {stats.get('win_rate', 0):.0%}, "
            text += f"avg error {stats.get('avg_error', 0):.0%}\n"

    text += "  Use this data to correct systematic biases in your estimates.\n\n"
    return text


class ProbabilityAgent(BaseAgent):
    name = "probability_agent"

    async def run(
        self,
        market: MarketData,
        research: ResearchResult,
        signal: Signal,
        calibration: dict | None = None,
    ) -> ProbabilityEstimate:
        """Estimate the true probability of a market outcome."""
        user_prompt = (
            f"Market: {market.question}\n"
            f"Description: {market.description[:500]}\n"
            f"Current market YES price: {market.outcome_yes_price:.2f}\n"
            f"Volume: ${market.volume:,.0f}\n\n"
            f"Research: {research.summary}\n"
            f"Key Factors: {', '.join(research.key_factors[:5])}\n"
        )

        # Add bull/bear cases if available
        if research.bull_case:
            user_prompt += f"Bull Case (YES): {research.bull_case}\n"
        if research.bear_case:
            user_prompt += f"Bear Case (NO): {research.bear_case}\n"

        user_prompt += (
            f"\nSignal Direction: {signal.direction}\n"
            f"Signal Strength: {signal.strength:.2f}\n"
            f"Signal Reasoning: {signal.reasoning[:300]}"
        )

        # Inject calibration history
        if calibration:
            user_prompt += _format_calibration(calibration)

        result = await llm_client.query(SYSTEM_PROMPT, user_prompt)

        if result.get("parse_error"):
            return ProbabilityEstimate(
                condition_id=market.condition_id,
                question=market.question,
                ai_probability=market.outcome_yes_price,
                market_probability=market.outcome_yes_price,
                confidence=0.2,
                reasoning="Probability estimation failed — defaulting to market price",
            )

        ai_prob = float(result.get("ai_probability", 0.5))
        ai_prob = max(0.01, min(0.99, ai_prob))  # clamp to avoid 0/1

        market_prob = market.outcome_yes_price
        edge = abs(ai_prob - market_prob)

        estimate = ProbabilityEstimate(
            condition_id=market.condition_id,
            question=market.question,
            ai_probability=ai_prob,
            market_probability=market_prob,
            confidence=float(result.get("confidence", 0.5)),
            edge=edge,
            reasoning=result.get("reasoning", ""),
        )

        await self.emit("probability_estimated", {
            "condition_id": market.condition_id,
            "ai_probability": ai_prob,
            "market_probability": market_prob,
            "edge": edge,
        })

        return estimate


probability_agent = ProbabilityAgent()

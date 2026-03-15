"""Reflection Agent — analyzes prediction mistakes after market resolution."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.llm_client import llm_client
from app.models.schemas import ReflectionResult
from app.models.db_models import Trade, TradeStatus, LessonLearned
from app.services.polymarket import polymarket_service


SYSTEM_PROMPT = """You are a prediction market analyst reviewing past trades. Analyze why a trade
succeeded or failed and extract actionable lessons.

Given the trade details and market resolution, produce a reflection.

Respond with JSON:
{
  "mistake_type": "<overconfidence|anchoring|timing|insufficient_research|correct_prediction|other>",
  "description": "<what happened and why>",
  "lesson": "<specific actionable lesson for future>",
  "severity": "<low|medium|high|critical>",
  "tags": ["<relevant tags>"],
  "calibration_note": "<how should probability estimates be adjusted>",
  "market_category": "<crypto|politics|macro|sports|entertainment|science|technology|weather|conflict|other>"
}"""


class ReflectionAgent(BaseAgent):
    name = "reflection_agent"

    async def run(self, db: AsyncSession) -> list[ReflectionResult]:
        """Check for resolved markets and analyze closed trades."""
        # Find open trades to check for resolution
        open_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = open_q.scalars().all()

        results = []

        for trade in open_trades:
            resolution = await polymarket_service.check_resolution(trade.condition_id)

            if not resolution or not resolution.get("resolved"):
                continue

            # Close the trade
            winning = resolution["winning_outcome"]

            # Skip if market hasn't clearly resolved (winning_outcome is None)
            if winning is None:
                continue

            trade_side = trade.side.value

            if trade_side == winning:
                # Win: get back size / entry_price
                payout = trade.size / trade.entry_price
                trade.pnl = payout - trade.size
            else:
                # Loss: lose entire stake
                trade.pnl = -trade.size

            trade.status = TradeStatus.CLOSED
            trade.exit_price = 1.0 if trade_side == winning else 0.0
            trade.resolution_outcome = winning
            trade.closed_at = datetime.now(timezone.utc)

            # LLM reflection
            user_prompt = (
                f"Market: {trade.market_question}\n"
                f"Our prediction: {trade.side.value} at {trade.ai_probability:.2f}\n"
                f"Market price: {trade.market_probability:.2f}\n"
                f"Our edge: {trade.edge:.2f}\n"
                f"Actual outcome: {winning}\n"
                f"PnL: {trade.pnl:+.2f}\n"
                f"Trade size: {trade.size:.2f}\n"
                f"Reasoning: {trade.entry_reasoning[:300]}"
            )

            try:
                result = await llm_client.query(SYSTEM_PROMPT, user_prompt)

                if not isinstance(result, dict) or result.get("parse_error"):
                    result = {}

                reflection = ReflectionResult(
                    trade_id=trade.id,
                    condition_id=trade.condition_id,
                    mistake_type=result.get("mistake_type", "other"),
                    description=result.get("description", "No analysis"),
                    lesson=result.get("lesson", "No lesson extracted"),
                    severity=result.get("severity", "medium"),
                    tags=result.get("tags", []),
                )

                # Store lesson in DB
                lesson = LessonLearned(
                    trade_id=trade.id,
                    condition_id=trade.condition_id,
                    category=result.get("market_category", "general"),
                    mistake_type=reflection.mistake_type,
                    description=reflection.description,
                    lesson=reflection.lesson,
                    confidence_before=trade.confidence,
                    severity=reflection.severity,
                    tags=reflection.tags,
                )
                db.add(lesson)

                trade.exit_reasoning = reflection.lesson
                results.append(reflection)

                self.log.info(
                    "trade_reflected",
                    trade_id=trade.id,
                    pnl=trade.pnl,
                    mistake=reflection.mistake_type,
                )

            except Exception as e:
                self.log.error("reflection_failed", trade_id=trade.id, error=str(e))

        if results:
            await self.emit("reflections_completed", {
                "count": len(results),
                "reflections": [r.model_dump() for r in results],
            })

        return results


reflection_agent = ReflectionAgent()

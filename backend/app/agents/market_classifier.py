"""Market Classifier Agent — classifies markets by category using LLM (batch mode)."""

from app.agents.base import BaseAgent
from app.core.llm_client import llm_client
from app.models.schemas import MarketData, ClassifiedMarket


SYSTEM_PROMPT = """Classify prediction markets. For each, give category and tradeable status.
Categories: crypto, politics, macro, sports, entertainment, science, tech, weather, conflict, other
Respond as JSON: {"markets":[{"n":1,"cat":"crypto","trade":true},{"n":2,"cat":"politics","trade":false}]}
Use short keys. trade=true if meaningful analysis is possible."""


class MarketClassifierAgent(BaseAgent):
    name = "market_classifier"

    async def run(self, markets: list[MarketData]) -> list[ClassifiedMarket]:
        """Classify a batch of markets using a single LLM call."""
        if not markets:
            return []

        # Use short numeric IDs to keep response compact
        lines = []
        for i, m in enumerate(markets):
            lines.append(f"{i+1}. {m.question[:80]} (YES={m.outcome_yes_price:.2f})")

        user_prompt = "Classify:\n" + "\n".join(lines)

        items_by_index = {}
        try:
            result = await llm_client.query(SYSTEM_PROMPT, user_prompt)

            if isinstance(result, dict) and "markets" in result:
                for item in result["markets"]:
                    idx = item.get("n", 0) - 1
                    items_by_index[idx] = item
            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        idx = item.get("n", 0) - 1
                        items_by_index[idx] = item
            elif isinstance(result, dict) and result.get("parse_error"):
                self.log.warning("classify_parse_error", fallback="all_tradeable")

        except Exception as e:
            self.log.error("classify_batch_error", error=str(e))

        # Map back to ClassifiedMarket objects
        classified = []
        for i, market in enumerate(markets):
            item = items_by_index.get(i)
            if item:
                cm = ClassifiedMarket(
                    condition_id=market.condition_id,
                    question=market.question,
                    category=item.get("cat", "other"),
                    subcategory="",
                    relevance_score=0.7,
                    tradeable=item.get("trade", True),
                )
            else:
                # Not in LLM response — default to tradeable
                cm = ClassifiedMarket(
                    condition_id=market.condition_id,
                    question=market.question,
                    category="other",
                    subcategory="",
                    relevance_score=0.5,
                    tradeable=True,
                )
            classified.append(cm)

        self.log.info("classification_complete", count=len(classified),
                      tradeable=sum(1 for c in classified if c.tradeable))

        await self.emit("markets_classified", {
            "count": len(classified),
            "categories": list({c.category for c in classified}),
        })

        return classified


market_classifier = MarketClassifierAgent()

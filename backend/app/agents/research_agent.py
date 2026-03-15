"""Research Agent — analyzes market events and extracts key factors."""

from app.agents.base import BaseAgent
from app.core.llm_client import llm_client
from app.models.schemas import MarketData, ResearchResult
from app.services.search_service import search_service


SYSTEM_PROMPT = """You are an expert prediction market researcher. Analyze the given market and produce
a research brief identifying key factors that will determine the outcome.

Consider:
- Historical precedents
- Current geopolitical/economic context
- Relevant data points and statistics
- Key uncertainties

Respond with JSON:
{
  "summary": "<2-3 sentence analysis>",
  "key_factors": ["<factor1>", "<factor2>", ...],
  "data_sources": ["<what data would help>"],
  "confidence": <0.0-1.0 how confident you are in this analysis>,
  "bull_case": "<why YES might win>",
  "bear_case": "<why NO might win>"
}"""


def _format_lessons(lessons: list[dict]) -> str:
    """Format past lessons into a prompt section."""
    if not lessons:
        return ""
    text = "\nLESSONS FROM PAST TRADES (apply these to your analysis):\n"
    for l in lessons[:10]:
        text += f"  - [{l.get('severity', 'medium').upper()}] {l.get('lesson', '')}\n"
    return text + "\n"


class ResearchAgent(BaseAgent):
    name = "research_agent"

    async def run(self, market: MarketData, lessons: list[dict] | None = None) -> ResearchResult:
        """Perform research analysis on a single market."""
        # Fetch real-time news and web search results
        search_results = await search_service.search(market.question, limit=3)

        # Format news results
        news_text = ""
        if search_results["news"]:
            news_text = "Recent News:\n"
            for i, article in enumerate(search_results["news"], 1):
                news_text += (
                    f"{i}. {article['title']}\n"
                    f"   Source: {article['source']} | Date: {article['date']}\n"
                    f"   {article['snippet']}\n\n"
                )

        # Format web search results
        web_text = ""
        if search_results["web"]:
            web_text = "Web Search Results:\n"
            for i, result in enumerate(search_results["web"], 1):
                web_text += (
                    f"{i}. {result['title']}\n"
                    f"   {result['snippet']}\n\n"
                )

        user_prompt = (
            f"Market: {market.question}\n"
            f"Description: {market.description[:800]}\n"
            f"Current YES price: {market.outcome_yes_price:.2f} "
            f"(market implies {market.outcome_yes_price:.0%} probability)\n"
            f"Volume: ${market.volume:,.0f}\n"
            f"End date: {market.end_date or 'Not specified'}\n\n"
        )

        # Inject lessons from past trades
        if lessons:
            user_prompt += _format_lessons(lessons)

        if news_text or web_text:
            user_prompt += f"{news_text}{web_text}\nBased on this real-time data, provide your analysis."
        else:
            user_prompt += "No recent news found — analyze based on general knowledge."

        result = await llm_client.query(SYSTEM_PROMPT, user_prompt)

        if result.get("parse_error"):
            return ResearchResult(
                condition_id=market.condition_id,
                question=market.question,
                summary="Research analysis failed — LLM parse error",
                confidence=0.2,
            )

        research = ResearchResult(
            condition_id=market.condition_id,
            question=market.question,
            summary=result.get("summary", "No summary"),
            key_factors=result.get("key_factors", []),
            data_sources=result.get("data_sources", []),
            confidence=float(result.get("confidence", 0.5)),
            bull_case=result.get("bull_case", ""),
            bear_case=result.get("bear_case", ""),
        )

        await self.emit("research_completed", {
            "condition_id": market.condition_id,
            "confidence": research.confidence,
        })

        return research


research_agent = ResearchAgent()

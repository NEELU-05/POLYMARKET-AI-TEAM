"""Market Scanner Agent — fetches active markets from Polymarket."""

from app.agents.base import BaseAgent
from app.services.polymarket import polymarket_service
from app.models.schemas import MarketData


class MarketScannerAgent(BaseAgent):
    name = "market_scanner"

    async def run(self, limit: int = 50) -> list[MarketData]:
        """Scan Polymarket for active markets."""
        markets = await polymarket_service.fetch_active_markets(limit=limit)

        # Filter out low-liquidity markets
        quality_markets = [
            m for m in markets
            if m.volume > 500 and m.liquidity > 200
        ]

        self.log.info(
            "scan_complete",
            total=len(markets),
            quality=len(quality_markets),
        )

        await self.emit("markets_scanned", {
            "count": len(quality_markets),
            "markets": [m.model_dump(mode="json") for m in quality_markets[:20]],
        })

        return quality_markets


market_scanner = MarketScannerAgent()

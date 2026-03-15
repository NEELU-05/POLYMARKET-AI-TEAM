"""Polymarket API service — fetches data from Gamma, Data, and CLOB APIs."""

import json
import httpx
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import MarketData

log = get_logger("polymarket_service")


def _parse_yes_price(raw) -> float:
    """Parse yes price from Polymarket API outcomePrices field.

    The API returns various formats:
      '[0.5,0.5]', '["0.995","0.005"]', [0.5, 0.5], etc.
    """
    if raw is None:
        return 0.5
    if isinstance(raw, list):
        return float(raw[0]) if raw else 0.5

    # String — try JSON parse (handles all quote variants)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            return float(parsed[0])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback: strip everything manually
    cleaned = raw.strip("[]").split(",")[0].strip().strip('"').strip("'")
    return float(cleaned)


def _parse_token_id(raw_market: dict) -> str:
    """Extract the YES token ID from Gamma API market data.

    The API provides clobTokenIds as a JSON string like '["token1","token2"]'
    where token1 = YES, token2 = NO.
    """
    raw = raw_market.get("clobTokenIds")
    if not raw:
        return ""
    if isinstance(raw, list):
        return str(raw[0]) if raw else ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            return str(parsed[0])
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return ""


class PolymarketService:
    """Client for Polymarket's public APIs."""

    def __init__(self) -> None:
        self._settings = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def gamma_url(self) -> str:
        return self.settings.gamma_api_url

    @property
    def data_url(self) -> str:
        return self.settings.data_api_url

    @property
    def clob_url(self) -> str:
        return self.settings.clob_api_url

    async def fetch_active_markets(self, limit: int = 50) -> list[MarketData]:
        """Fetch active markets from Gamma API."""
        url = f"{self.gamma_url}/markets"
        params = {
            "limit": limit,
            "active": True,
            "closed": False,
            "order": "volume",
            "ascending": False,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                raw_markets = resp.json()
        except Exception as e:
            log.error("gamma_fetch_failed", error=str(e))
            return []

        markets = []
        for m in raw_markets:
            try:
                yes_price = _parse_yes_price(m.get("outcomePrices"))
                no_price = 1.0 - yes_price

                end_date = None
                if m.get("endDate"):
                    try:
                        end_date = datetime.fromisoformat(
                            m["endDate"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                market = MarketData(
                    condition_id=m.get("conditionId", m.get("id", "")),
                    question=m.get("question", "Unknown"),
                    description=m.get("description", ""),
                    outcome_yes_price=yes_price,
                    outcome_no_price=no_price,
                    volume=float(m.get("volume", 0)),
                    liquidity=float(m.get("liquidity", 0)),
                    end_date=end_date,
                    market_slug=m.get("slug", ""),
                    token_id=_parse_token_id(m),
                )
                markets.append(market)
            except Exception as e:
                log.warning("market_parse_error", error=str(e), raw=str(m)[:200])

        log.info("markets_fetched", count=len(markets))
        return markets

    async def fetch_market_by_id(self, condition_id: str) -> MarketData | None:
        """Fetch a single market by condition ID."""
        url = f"{self.gamma_url}/markets"
        params = {"condition_id": condition_id}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    return None

                m = data[0] if isinstance(data, list) else data
                yes_price = _parse_yes_price(m.get("outcomePrices"))

                return MarketData(
                    condition_id=m.get("conditionId", m.get("id", "")),
                    question=m.get("question", "Unknown"),
                    description=m.get("description", ""),
                    outcome_yes_price=yes_price,
                    outcome_no_price=1.0 - yes_price,
                    volume=float(m.get("volume", 0)),
                    liquidity=float(m.get("liquidity", 0)),
                    market_slug=m.get("slug", ""),
                    token_id=_parse_token_id(m),
                )
        except Exception as e:
            log.error("market_fetch_by_id_failed", condition_id=condition_id, error=str(e))
            return None

    async def fetch_orderbook(self, token_id: str) -> dict:
        """Fetch orderbook from CLOB API."""
        url = f"{self.clob_url}/book"
        params = {"token_id": token_id}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("orderbook_fetch_failed", token_id=token_id, error=str(e))
            return {"bids": [], "asks": []}

    async def fetch_market_trades(self, condition_id: str, limit: int = 20) -> list[dict]:
        """Fetch recent trades from Data API."""
        url = f"{self.data_url}/trades"
        params = {"market": condition_id, "limit": limit}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("trades_fetch_failed", condition_id=condition_id, error=str(e))
            return []

    async def check_resolution(self, condition_id: str) -> dict | None:
        """Check if a market has resolved."""
        url = f"{self.gamma_url}/markets"
        params = {"condition_id": condition_id}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    return None

                m = data[0] if isinstance(data, list) else data
                if m.get("resolved") or m.get("closed"):
                    # Try to use actual resolution field if available
                    winning_outcome = m.get("winningSide") or m.get("winning_outcome")

                    # Fallback: if no explicit resolution, use price (extreme means resolved)
                    if not winning_outcome:
                        yes_price = _parse_yes_price(m.get("outcomePrices"))
                        winning_outcome = "yes" if yes_price > 0.9 else ("no" if yes_price < 0.1 else None)

                    return {
                        "resolved": True,
                        "outcome": m.get("resolutionSource", ""),
                        "winning_outcome": winning_outcome,
                    }
        except Exception as e:
            log.error("resolution_check_failed", error=str(e))

        return None

    # --- Data API (https://data-api.polymarket.com) ---

    async def fetch_market_open_interest(self, condition_id: str) -> dict:
        """Fetch open interest data for a market from Data API."""
        url = f"{self.data_url}/value"
        params = {"market": condition_id}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.warning("open_interest_fetch_failed", condition_id=condition_id[:20], error=str(e))
            return {}

    async def fetch_market_timeseries(self, token_id: str, fidelity: int = 60) -> list[dict]:
        """Fetch price timeseries for a token from Data API."""
        url = f"{self.data_url}/prices-history"
        params = {"market": token_id, "interval": "max", "fidelity": fidelity}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("history", data) if isinstance(data, dict) else data
        except Exception as e:
            log.warning("timeseries_fetch_failed", error=str(e))
            return []

    async def fetch_global_events(self, limit: int = 20) -> list[dict]:
        """Fetch top events from Gamma API."""
        url = f"{self.gamma_url}/events"
        params = {"limit": limit, "active": True, "closed": False, "order": "volume", "ascending": False}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.warning("events_fetch_failed", error=str(e))
            return []

    async def search_markets(self, query: str, limit: int = 10) -> list[dict]:
        """Search markets via Gamma API."""
        url = f"{self.gamma_url}/markets"
        params = {"_q": query, "limit": limit, "active": True, "closed": False}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.warning("search_failed", query=query, error=str(e))
            return []


# Singleton
polymarket_service = PolymarketService()

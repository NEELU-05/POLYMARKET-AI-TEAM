"""Search service for real-time web and news data.

Provides web search (Serper) and news search (News API) for market analysis.
"""

import asyncio
import httpx
from typing import Any
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("search_service")


class SearchService:
    """Aggregates web and news search results for market research."""

    def __init__(self) -> None:
        self._settings = None

    @property
    def settings(self):
        """Lazy-load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def web_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the web using Serper API.

        Args:
            query: Search query
            limit: Max results to return (default 5)

        Returns:
            List of dicts with keys: title, snippet, url, date (if available)
        """
        if not self.settings.serper_api_key:
            log.warning("serper_api_key not configured, skipping web search")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "num": limit},
                    headers={"X-API-KEY": self.settings.serper_api_key},
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic", [])[:limit]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "date": item.get("date", ""),  # Serper may include date
                    "source": "serper",
                })
            return results

        except httpx.HTTPStatusError as e:
            log.error("serper_http_error", status=e.response.status_code, body=str(e)[:200])
            return []
        except Exception as e:
            log.error("web_search_error", error=str(e))
            return []

    async def news_search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search news using News API.

        Args:
            query: Search query
            limit: Max results to return (default 5)

        Returns:
            List of dicts with keys: title, snippet, url, date, source
        """
        if not self.settings.news_api_key:
            log.warning("news_api_key not configured, skipping news search")
            return []

        try:
            # News API: search news from last 7 days sorted by recency
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": limit,
                        "from": (datetime.now() - timedelta(days=7)).isoformat(),
                    },
                    headers={"X-Api-Key": self.settings.news_api_key},
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for article in data.get("articles", [])[:limit]:
                published = article.get("publishedAt", "")
                # Parse ISO datetime and format as readable string
                try:
                    dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = published

                results.append({
                    "title": article.get("title", ""),
                    "snippet": article.get("description", ""),
                    "url": article.get("url", ""),
                    "date": date_str,
                    "source": article.get("source", {}).get("name", "Unknown"),
                })
            return results

        except httpx.HTTPStatusError as e:
            log.error("news_api_http_error", status=e.response.status_code, body=str(e)[:200])
            return []
        except Exception as e:
            log.error("news_search_error", error=str(e))
            return []

    async def search(self, query: str, limit: int = 5) -> dict[str, list[dict[str, Any]]]:
        """Combined web + news search.

        Returns results from both Serper and News API for comprehensive research.

        Args:
            query: Search query
            limit: Max results per source

        Returns:
            Dict with keys "web" and "news", each containing list of search results
        """
        web_results, news_results = await asyncio.gather(
            self.web_search(query, limit),
            self.news_search(query, limit),
        )

        return {
            "web": web_results,
            "news": news_results,
        }


# Singleton
search_service = SearchService()


# For convenience, expose functions at module level
async def web_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search the web."""
    return await search_service.web_search(query, limit)


async def news_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search news."""
    return await search_service.news_search(query, limit)


async def search(query: str, limit: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Combined search (web + news)."""
    return await search_service.search(query, limit)

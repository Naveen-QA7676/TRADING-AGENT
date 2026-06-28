"""
Web Search Agent — uses SerpAPI for Google search results.
Runs daily morning queries for fresh market intelligence.
"""

import httpx
from loguru import logger
from backend.config import settings


MORNING_QUERIES = [
    "US stock market close yesterday S&P 500 Nasdaq results",
    "India Nifty 50 outlook today FII DII data",
    "SGX GIFT Nifty futures live today",
    "India economic calendar events this week RBI",
    "NSE BSE announcements today corporate actions",
    "Global crude oil gold DXY dollar today",
    "India VIX nifty options PCR today",
    "India budget RBI monetary policy latest",
]


class WebSearchAgent:

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=20.0)

    async def search(self, query: str, num_results: int = 5) -> list[dict]:
        """Single SerpAPI search."""
        if not settings.serpapi_key:
            logger.warning("No SerpAPI key configured. Skipping web search.")
            return []
        try:
            resp = await self._client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "num": num_results,
                    "api_key": settings.serpapi_key,
                    "engine": "google",
                    "hl": "en",
                    "gl": "in",
                },
            )
            data = resp.json()
            organic = data.get("organic_results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "url": r.get("link", ""),
                    "source": r.get("displayed_link", ""),
                }
                for r in organic
            ]
        except Exception as e:
            logger.error(f"SerpAPI error for '{query}': {e}")
            return []

    async def morning_research(self) -> dict[str, list[dict]]:
        """Run all morning research queries."""
        results = {}
        for query in MORNING_QUERIES:
            results[query] = await self.search(query)
        logger.info(f"Morning research complete: {len(results)} queries")
        return results

    async def search_stock(self, symbol: str) -> list[dict]:
        """Search for latest news and analysis on a specific stock."""
        queries = [
            f"{symbol} stock news today NSE",
            f"{symbol} NSE technical analysis today",
            f"{symbol} quarterly results earnings latest",
        ]
        all_results = []
        for q in queries:
            all_results.extend(await self.search(q, num_results=3))
        return all_results

    async def close(self):
        await self._client.aclose()


search_agent = WebSearchAgent()

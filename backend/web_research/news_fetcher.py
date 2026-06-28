"""
News Intelligence — fetches from NewsAPI, RSS feeds (ET, Moneycontrol, BSE, NSE).
Classifies each article for sentiment, impact, and affected symbols.
"""

import asyncio
import feedparser
import httpx
from datetime import datetime, timedelta
from loguru import logger

from backend.config import settings


STOCK_RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rss.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://feeds.feedburner.com/ndtvprofit-latest",
]

MACRO_RSS_FEEDS = [
    "https://economictimes.indiatimes.com/news/economy/rss.cms",
    "https://www.livemint.com/rss/markets",
]


class NewsFetcher:

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    async def fetch_newsapi(self, query: str = "India stock market NSE Nifty", hours: int = 6) -> list[dict]:
        """Fetch from NewsAPI.org."""
        if not settings.news_api_key:
            return []
        try:
            from_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
            resp = await self._client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": from_time,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 50,
                    "apiKey": settings.news_api_key,
                },
            )
            data = resp.json()
            articles = data.get("articles", [])
            return [
                {
                    "source": a.get("source", {}).get("name", "NewsAPI"),
                    "headline": a.get("title", ""),
                    "url": a.get("url", ""),
                    "published_at": a.get("publishedAt", ""),
                    "content": a.get("description", "") or a.get("content", ""),
                }
                for a in articles
                if a.get("title")
            ]
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []

    async def fetch_rss(self, url: str) -> list[dict]:
        """Fetch and parse a single RSS feed."""
        try:
            resp = await self._client.get(url)
            feed = feedparser.parse(resp.text)
            items = []
            for entry in feed.entries[:20]:
                items.append({
                    "source": feed.feed.get("title", url),
                    "headline": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "published_at": entry.get("published", ""),
                    "content": entry.get("summary", ""),
                })
            return items
        except Exception as e:
            logger.error(f"RSS fetch error ({url}): {e}")
            return []

    async def fetch_all_rss(self) -> list[dict]:
        """Fetch all configured RSS feeds concurrently."""
        all_feeds = STOCK_RSS_FEEDS + MACRO_RSS_FEEDS
        tasks = [self.fetch_rss(url) for url in all_feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        articles = []
        for r in results:
            if isinstance(r, list):
                articles.extend(r)
        return articles

    async def fetch_all(self) -> list[dict]:
        """Fetch news from all sources."""
        newsapi_task = self.fetch_newsapi()
        rss_task = self.fetch_all_rss()
        newsapi_articles, rss_articles = await asyncio.gather(newsapi_task, rss_task)
        all_articles = newsapi_articles + rss_articles

        # Deduplicate by URL
        seen = set()
        unique = []
        for a in all_articles:
            if a["url"] not in seen and a["headline"]:
                seen.add(a["url"])
                unique.append(a)

        logger.info(f"Fetched {len(unique)} unique news articles")
        return unique

    async def close(self):
        await self._client.aclose()


news_fetcher = NewsFetcher()

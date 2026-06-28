"""
News API — latest news items, breaking news feed, symbol-specific news.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.database import get_db
from backend.models import NewsItem
from backend.web_research.news_fetcher import news_fetcher
from backend.web_research.search_agent import web_search_agent
from loguru import logger

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/")
async def get_news(
    limit: int = Query(50, ge=1, le=200),
    sentiment: str = Query(None),
    impact: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Latest news, optionally filtered by sentiment/impact."""
    query = select(NewsItem).order_by(desc(NewsItem.published_at)).limit(limit)
    if sentiment:
        query = query.where(NewsItem.sentiment == sentiment.upper())
    if impact:
        query = query.where(NewsItem.impact == impact.upper())
    result = await db.execute(query)
    items = result.scalars().all()
    return [_serialize(n) for n in items]


@router.get("/breaking")
async def get_breaking_news(db: AsyncSession = Depends(get_db)):
    """Breaking/high-impact news only."""
    result = await db.execute(
        select(NewsItem)
        .where(NewsItem.impact.in_(["HIGH", "BREAKING"]))
        .order_by(desc(NewsItem.published_at))
        .limit(20)
    )
    return [_serialize(n) for n in result.scalars().all()]


@router.get("/symbol/{symbol}")
async def get_symbol_news(symbol: str, db: AsyncSession = Depends(get_db)):
    """News affecting a specific symbol."""
    result = await db.execute(
        select(NewsItem)
        .where(NewsItem.affected_symbols.contains([symbol]))
        .order_by(desc(NewsItem.published_at))
        .limit(20)
    )
    return [_serialize(n) for n in result.scalars().all()]


@router.post("/refresh")
async def refresh_news():
    """Manually trigger a news refresh."""
    try:
        items = await news_fetcher.fetch_all()
        return {"fetched": len(items), "status": "OK"}
    except Exception as e:
        logger.error(f"News refresh error: {e}")
        return {"error": str(e)}


@router.get("/search/{symbol}")
async def search_symbol_news(symbol: str):
    """Web search for latest news about a stock."""
    try:
        results = await web_search_agent.search_stock(symbol)
        return {"symbol": symbol, "results": results}
    except Exception as e:
        return {"error": str(e)}


def _serialize(n: NewsItem) -> dict:
    return {
        "id": n.id,
        "headline": n.headline,
        "source": n.source,
        "url": n.url,
        "sentiment": n.sentiment,
        "impact": n.impact,
        "affected_symbols": n.affected_symbols,
        "summary": n.summary,
        "published_at": n.published_at.isoformat() if n.published_at else None,
    }

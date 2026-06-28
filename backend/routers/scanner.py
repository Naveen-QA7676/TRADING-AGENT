"""
Scanner API — current scan results, watchlist, morning brief data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db
from backend.models import WatchlistItem
from backend.redis_client import redis_client, KEYS
from backend.web_research.global_data import global_data_fetcher
from backend.web_research.nse_scraper import nse_scraper
import json
from pydantic import BaseModel

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/morning-brief")
async def get_morning_brief():
    """Pre-market intelligence: global data, FII/DII, India VIX, regime."""
    try:
        global_data = await global_data_fetcher.fetch_all()
        context = global_data_fetcher.interpret_global_context(global_data)

        fii_dii = None
        try:
            fii_dii = await nse_scraper.get_fii_dii_data()
        except Exception:
            pass

        regime_raw = await redis_client.get(KEYS["market_regime"])
        regime = regime_raw.decode() if regime_raw else "UNKNOWN"

        return {
            "global_data": global_data,
            "global_context": context,
            "fii_dii": fii_dii,
            "market_regime": regime,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/candidates")
async def get_scan_candidates():
    """Latest scan candidates from Redis."""
    raw = await redis_client.get("scanner:candidates")
    if not raw:
        return {"candidates": [], "scanned_at": None}
    data = json.loads(raw)
    return data


@router.get("/regime")
async def get_market_regime():
    """Current market regime from Redis."""
    raw = await redis_client.get(KEYS["market_regime"])
    regime = raw.decode() if raw else "UNKNOWN"
    return {"regime": regime}


@router.get("/watchlist")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """User's saved watchlist."""
    result = await db.execute(
        select(WatchlistItem).order_by(desc(WatchlistItem.added_at))
    )
    items = result.scalars().all()
    return [
        {"id": w.id, "symbol": w.symbol, "notes": w.notes, "added_at": str(w.added_at)}
        for w in items
    ]


class WatchlistAddRequest(BaseModel):
    symbol: str
    notes: str = ""


@router.post("/watchlist")
async def add_to_watchlist(body: WatchlistAddRequest, db: AsyncSession = Depends(get_db)):
    item = WatchlistItem(symbol=body.symbol.upper(), notes=body.notes)
    db.add(item)
    await db.commit()
    return {"status": "ADDED", "symbol": body.symbol.upper()}


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.symbol == symbol.upper())
    )
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.commit()
    return {"status": "REMOVED", "symbol": symbol.upper()}

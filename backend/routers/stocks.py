"""
Stocks API — stock explorer: quote, historical data, technical snapshot, fundamentals.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
from datetime import date, timedelta

from backend.database import get_db
from backend.broker.kite_auth import kite_session
from backend.technical.indicators import indicator_engine
from backend.technical.market_structure import MarketStructureAnalyzer
from backend.technical.support_resistance import SupportResistanceEngine
from backend.web_research.screener_scraper import screener_scraper

router = APIRouter(prefix="/stocks", tags=["stocks"])

_ms_analyzer = MarketStructureAnalyzer()
_sr_engine = SupportResistanceEngine()


@router.get("/{symbol}/quote")
async def get_quote(symbol: str):
    """Live quote for a symbol."""
    try:
        quote = kite_session.get_quote([f"NSE:{symbol}"])
        data = quote.get(f"NSE:{symbol}", {})
        return {
            "symbol": symbol,
            "ltp": data.get("last_price"),
            "open": data.get("ohlc", {}).get("open"),
            "high": data.get("ohlc", {}).get("high"),
            "low": data.get("ohlc", {}).get("low"),
            "close": data.get("ohlc", {}).get("close"),
            "volume": data.get("volume"),
            "change_pct": data.get("net_change"),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{symbol}/candles")
async def get_candles(
    symbol: str,
    interval: str = Query("5minute", regex="^(minute|3minute|5minute|15minute|30minute|60minute|day)$"),
    days: int = Query(5, ge=1, le=60),
):
    """OHLCV candlestick data."""
    try:
        from_dt = date.today() - timedelta(days=days)
        to_dt = date.today()
        data = kite_session.get_historical_data(
            symbol=symbol,
            from_date=from_dt,
            to_date=to_dt,
            interval=interval,
        )
        return {"symbol": symbol, "interval": interval, "candles": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{symbol}/technical")
async def get_technical_snapshot(symbol: str):
    """Full multi-timeframe technical indicator snapshot."""
    try:
        results = {}
        timeframes = {
            "5m": ("5minute", 5),
            "15m": ("15minute", 15),
            "1h": ("60minute", 30),
            "daily": ("day", 100),
        }
        for tf_name, (interval, days) in timeframes.items():
            try:
                candles = kite_session.get_historical_data(
                    symbol=symbol,
                    from_date=date.today() - timedelta(days=days),
                    to_date=date.today(),
                    interval=interval,
                )
                if candles:
                    df = pd.DataFrame(candles)
                    df.columns = ["date", "open", "high", "low", "close", "volume"]
                    tf_result = indicator_engine.compute_all(df)
                    results[tf_name] = {
                        "bull_score": tf_result.bull_score,
                        "buy_count": tf_result.buy_count,
                        "sell_count": tf_result.sell_count,
                        "neutral_count": tf_result.neutral_count,
                        "rsi": tf_result.rsi.value if tf_result.rsi else None,
                        "macd_signal": tf_result.macd.signal if tf_result.macd else None,
                        "vwap": tf_result.vwap.value if tf_result.vwap else None,
                    }
            except Exception:
                results[tf_name] = None

        return {"symbol": symbol, "timeframes": results}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{symbol}/fundamentals")
async def get_fundamentals(symbol: str):
    """Fundamental data from Screener.in."""
    try:
        data = await screener_scraper.get_fundamentals(symbol)
        grade = screener_scraper.grade_fundamentals(data) if data else "N/A"
        return {"symbol": symbol, "grade": grade, "data": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{symbol}/structure")
async def get_market_structure(symbol: str):
    """Market structure: swing highs/lows, order blocks, FVG."""
    try:
        candles = kite_session.get_historical_data(
            symbol=symbol,
            from_date=date.today() - timedelta(days=10),
            to_date=date.today(),
            interval="15minute",
        )
        if not candles:
            return {"symbol": symbol, "error": "No data"}
        df = pd.DataFrame(candles)
        df.columns = ["date", "open", "high", "low", "close", "volume"]
        ms = _ms_analyzer.analyze(df)
        obs = _ms_analyzer.find_order_blocks(df)
        fvgs = _ms_analyzer.find_fvg(df)
        levels = _sr_engine.find_levels(df)
        return {
            "symbol": symbol,
            "trend": ms.trend,
            "last_hhhl": ms.last_hh_hl,
            "bos": ms.bos_detected,
            "choch": ms.choch_detected,
            "order_blocks": [
                {"dir": ob.direction, "high": ob.high, "low": ob.low}
                for ob in obs[:5]
            ],
            "fvgs": [
                {"dir": fvg.direction, "high": fvg.high, "low": fvg.low, "filled": fvg.is_filled}
                for fvg in fvgs[:5]
            ],
            "key_levels": [
                {"price": lv.price, "type": lv.level_type, "strength": lv.strength}
                for lv in levels[:10]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

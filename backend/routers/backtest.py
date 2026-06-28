"""
Backtest API — run backtests on historical data for a symbol + strategy.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger
import asyncio

router = APIRouter(prefix="/backtest", tags=["backtest"])

AVAILABLE_STRATEGIES = {
    "vwap_bounce": "vwap_bounce_strategy",
    "orb":         "orb_strategy",
}


class BacktestRequest(BaseModel):
    symbol:   str
    strategy: str = "vwap_bounce"  # key from AVAILABLE_STRATEGIES
    days:     int = 60
    capital:  float = 150000.0
    risk_pct: float = 0.01


@router.post("/run")
async def run_backtest(body: BacktestRequest):
    if body.strategy not in AVAILABLE_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy. Available: {list(AVAILABLE_STRATEGIES)}"
        )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_sync, body)
        return result
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_sync(body: BacktestRequest) -> dict:
    from backend.backtest.backtest_engine import (
        BacktestEngine, vwap_bounce_strategy, orb_strategy
    )
    from backend.pipeline import _get_token, _fetch_candles
    from datetime import datetime, timedelta

    token = _get_token(body.symbol)
    if not token:
        raise ValueError(f"No instrument token found for {body.symbol}")

    df = _fetch_candles(token, "15minute", body.days)
    if df.empty:
        raise ValueError(f"No historical data for {body.symbol}")

    strategy_map = {
        "vwap_bounce": vwap_bounce_strategy,
        "orb":         orb_strategy,
    }
    strategy_fn = strategy_map[body.strategy]

    engine = BacktestEngine(
        capital=body.capital,
        risk_per_trade=body.risk_pct,
    )
    results = engine.run(df, strategy_fn, symbol=body.symbol)

    # Serialize
    return {
        "symbol":        results.symbol,
        "strategy":      body.strategy,
        "days":          body.days,
        "total_trades":  results.total_trades,
        "wins":          results.wins,
        "losses":        results.losses,
        "win_rate":      round(results.win_rate, 3),
        "expectancy":    round(results.expectancy, 3),
        "profit_factor": round(results.profit_factor, 2) if results.profit_factor != float("inf") else 999,
        "sharpe_ratio":  round(results.sharpe_ratio, 2),
        "max_drawdown":  round(results.max_drawdown, 3),
        "total_pnl":     round(results.total_pnl, 2),
        "avg_win":       round(results.avg_win, 2),
        "avg_loss":      round(results.avg_loss, 2),
        "best_trade":    round(results.best_trade, 2),
        "worst_trade":   round(results.worst_trade, 2),
        "avg_bars_held": round(results.avg_bars_held, 1),
        "equity_curve":  results.equity_curve[::5],  # subsample for response size
        "trades": [
            {
                "date":        t.date.isoformat() if hasattr(t.date, "isoformat") else str(t.date),
                "direction":   t.direction,
                "entry":       round(t.entry, 2),
                "exit_price":  round(t.exit_price, 2),
                "exit_reason": t.exit_reason,
                "pnl":         round(t.pnl, 2),
                "r_multiple":  round(t.r_multiple, 2),
                "bars_held":   t.bars_held,
            }
            for t in results.trades
        ],
    }


@router.get("/strategies")
async def list_strategies():
    return {"strategies": list(AVAILABLE_STRATEGIES.keys())}

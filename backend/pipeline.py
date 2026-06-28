"""
Single-symbol analysis pipeline.
Called by the scheduler for each candidate during market hours.
Collects data from all specialist agents and feeds to the Supervisor.
"""

import asyncio
import json
from datetime import datetime, timedelta
from loguru import logger

import pandas as pd

from backend.config import settings
from backend.broker.kite_auth import kite_session
from backend.broker.kite_websocket import ws_manager
from backend.redis_client import redis_client, CHANNELS, KEYS
from backend.technical.indicators import indicator_engine
from backend.agents.supervisor_agent import supervisor_agent, SupervisorInput
from backend.agents.risk_and_learning.risk_manager_agent import risk_manager_agent
from backend.routers.agents_status import update_agent


# ─── Instrument token cache ──────────────────────────────────────────────────

_token_cache: dict[str, int] = {}


def _get_token(symbol: str) -> int | None:
    if symbol in _token_cache:
        return _token_cache[symbol]
    try:
        instruments = kite_session.get_instruments("NSE")
        for inst in instruments:
            if inst["tradingsymbol"] == symbol and inst["segment"] == "NSE":
                _token_cache[inst["tradingsymbol"]] = inst["instrument_token"]
        return _token_cache.get(symbol)
    except Exception as e:
        logger.error(f"Token lookup failed for {symbol}: {e}")
        return None


def _fetch_candles(token: int, interval: str, days: int = 5) -> pd.DataFrame:
    """Fetch historical OHLCV data and return as DataFrame."""
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)
    try:
        raw = kite_session.get_historical_data(token, from_date, to_date, interval)
        if not raw:
            return pd.DataFrame()
        df = pd.DataFrame(raw)
        df.rename(columns={"date": "time", "open": "open", "high": "high",
                            "low": "low", "close": "close", "volume": "volume"}, inplace=True)
        df = df.sort_values("time").reset_index(drop=True)
        return df
    except Exception as e:
        logger.warning(f"Candle fetch failed (token={token}, interval={interval}): {e}")
        return pd.DataFrame()


def _kite_interval(tf: str) -> tuple[str, int]:
    """Map tf name → (kite_interval, days_back)."""
    mapping = {
        "5m":    ("5minute",  3),
        "15m":   ("15minute", 5),
        "1h":    ("60minute", 10),
        "daily": ("day",      365),
    }
    return mapping.get(tf, ("15minute", 5))


# ─── Pipeline ────────────────────────────────────────────────────────────────

async def analyze_symbol(
    symbol: str,
    ltp: float,
    market_regime: str,
    macro_context: dict,
    news_context: dict,
    sector_context: dict,
    global_context: dict,
    options_data: dict,
    portfolio_state: dict,
    daily_pnl: float,
    nifty_token: int | None = None,
) -> dict | None:
    """
    Full pipeline for one symbol. Returns suggestion dict or None.
    All heavy Kite API calls run in a thread executor to avoid blocking the event loop.
    """
    update_agent("supervisor_agent", "ACTIVE", f"Analyzing {symbol} @ ₹{ltp:.2f}")
    loop = asyncio.get_event_loop()

    try:
        token = await loop.run_in_executor(None, _get_token, symbol)
        if not token:
            logger.warning(f"No instrument token for {symbol} — skipping")
            return None

        # ── Fetch OHLCV across timeframes ──────────────────────────────────
        dfs: dict[str, pd.DataFrame] = {}
        for tf in ("5m", "15m", "1h", "daily"):
            kite_iv, days = _kite_interval(tf)
            dfs[tf] = await loop.run_in_executor(None, _fetch_candles, token, kite_iv, days)

        if dfs["15m"].empty:
            logger.warning(f"No 15m candles for {symbol} — skipping")
            return None

        # ── Technical indicators ────────────────────────────────────────────
        def _compute_indicators():
            results = {}
            for tf, df in dfs.items():
                if df.empty:
                    results[tf] = {}
                    continue
                try:
                    ind = indicator_engine.compute_all(df, tf)
                    results[tf] = ind.__dict__ if hasattr(ind, "__dict__") else {}
                except Exception as e:
                    logger.warning(f"Indicator error for {symbol} {tf}: {e}")
                    results[tf] = {}
            return results

        indicators = await loop.run_in_executor(None, _compute_indicators)

        # ── Nifty data for market structure ────────────────────────────────
        nifty_15m = pd.DataFrame()
        nifty_daily = pd.DataFrame()
        if nifty_token:
            nifty_15m  = await loop.run_in_executor(None, _fetch_candles, nifty_token, "15minute", 5)
            nifty_daily = await loop.run_in_executor(None, _fetch_candles, nifty_token, "day", 365)

        # ── Order flow from WebSocket ───────────────────────────────────────
        tick = ws_manager.get_latest_tick(token)
        order_flow: dict = {}
        if tick:
            order_flow = {
                "last_price": tick.get("last_price", ltp),
                "volume": tick.get("volume", 0),
                "buy_quantity": tick.get("buy_quantity", 0),
                "sell_quantity": tick.get("sell_quantity", 0),
                "depth": tick.get("depth", {}),
            }

        # ── Risk + position sizing ──────────────────────────────────────────
        atr_val = float(indicators.get("15m", {}).get("atr", {}) or 0)
        atr_avg = atr_val  # simplify: same for quick eval

        # Rough SL estimate for risk manager pre-check (1 ATR below)
        rough_sl   = ltp - max(atr_val, ltp * 0.01)
        rough_t1   = ltp + atr_val * 2

        risk_data = await loop.run_in_executor(
            None,
            risk_manager_agent.evaluate,
            ltp, rough_sl, rough_t1, daily_pnl,
            portfolio_state.get("open_positions_count", 0),
            atr_val, atr_avg, dfs.get("5m"),
        )

        if not risk_data.get("trading_allowed", False):
            logger.info(f"Risk check blocked {symbol}: {risk_data.get('warnings', [])[:1]}")
            return None

        # ── Historical edge ─────────────────────────────────────────────────
        historical_edge: dict = {}  # populated from DB in production

        # ── Supervisor input ────────────────────────────────────────────────
        strategy_candidates = [
            {"name": "VWAP Bounce",      "condition": "Price at VWAP + POC cluster"},
            {"name": "ORB Breakout",     "condition": "Break of opening 15m range"},
            {"name": "EMA Pullback",     "condition": "Pullback to EMA20 in trend"},
            {"name": "Volume Breakout",  "condition": "Price + volume breakout above resistance"},
        ]

        sup_input = SupervisorInput(
            symbol=symbol,
            ltp=ltp,
            market_regime=market_regime,
            market_structure={"regime": market_regime, "score": 7},
            macro_context=macro_context,
            news_context=news_context,
            sector_context=sector_context,
            global_context=global_context,
            sentiment_context={},
            order_flow=order_flow,
            volume_profile={},
            microstructure={},
            technical_5m=indicators.get("5m", {}),
            technical_15m=indicators.get("15m", {}),
            technical_1h=indicators.get("1h", {}),
            technical_daily=indicators.get("daily", {}),
            strategy_candidates=strategy_candidates,
            options_data=options_data,
            risk_data=risk_data,
            portfolio_state=portfolio_state,
            historical_edge=historical_edge,
            capital=settings.capital,
        )

        # Run supervisor synchronously in executor
        supervisor_output = await loop.run_in_executor(None, supervisor_agent.analyze, sup_input)

        update_agent(
            "supervisor_agent", "WAITING",
            f"{symbol}: score={supervisor_output.confidence_score}, "
            f"{'SUGGEST' if supervisor_output.suggestion else 'NO TRADE'}"
        )

        if not supervisor_output.suggestion:
            logger.info(f"No suggestion for {symbol}: {supervisor_output.no_suggestion_reason}")
            return None

        if supervisor_output.confidence_score < settings.min_confidence_score:
            logger.info(f"Low confidence for {symbol}: {supervisor_output.confidence_score}")
            return None

        suggestion = supervisor_output.suggestion
        # Attach risk data
        suggestion["quantity"]        = risk_data.get("quantity", 1)
        suggestion["risk_amount"]     = risk_data.get("risk_amount", 0)
        suggestion["risk_pct"]        = risk_data.get("risk_pct", 1.0)
        suggestion["stage_outputs"]   = supervisor_output.stage_outputs
        suggestion["confidence_score"] = supervisor_output.confidence_score
        suggestion["symbol"] = symbol

        return suggestion

    except Exception as e:
        logger.error(f"Pipeline error for {symbol}: {e}")
        update_agent("supervisor_agent", "ERROR", f"Error on {symbol}: {str(e)[:80]}")
        return None


async def save_suggestion(suggestion: dict, db_session) -> int | None:
    """Persist suggestion to PostgreSQL and publish to Redis."""
    from backend.models import TradeSuggestion, TradeStatus
    from datetime import timezone

    try:
        now = datetime.now(timezone.utc)
        entry_low  = float(suggestion.get("entry_price_low",  suggestion.get("entry_price", 0)))
        entry_high = float(suggestion.get("entry_price_high", suggestion.get("entry_price", 0)))

        s = TradeSuggestion(
            symbol            = suggestion.get("symbol"),
            direction         = suggestion.get("direction", "LONG"),
            strategy_name     = suggestion.get("strategy_name", ""),
            confidence_score  = suggestion.get("confidence_score", 0),
            entry_price_low   = entry_low,
            entry_price_high  = entry_high,
            stop_loss         = float(suggestion.get("stop_loss", 0)),
            target_1          = float(suggestion.get("target_1", 0)),
            target_2          = float(suggestion.get("target_2", 0) or 0),
            quantity          = int(suggestion.get("quantity", 0)),
            risk_amount       = float(suggestion.get("risk_amount", 0)),
            risk_pct          = float(suggestion.get("risk_pct", 1.0)),
            rr_ratio          = float(suggestion.get("rr_ratio", 0) or 0),
            win_probability   = float(suggestion.get("win_probability", 0.5) or 0.5),
            agent_scores      = suggestion.get("agent_scores", {}),
            reasons_for       = suggestion.get("reasons_for", []),
            reasons_against   = suggestion.get("reasons_against", []),
            status            = TradeStatus.SUGGESTED,
            created_at        = now,
            expires_at        = now + timedelta(minutes=10),
        )
        db_session.add(s)
        await db_session.commit()
        await db_session.refresh(s)

        # Publish to Redis pub/sub
        payload = json.dumps({
            **suggestion,
            "id":         s.id,
            "created_at": now.isoformat(),
            "valid_until": (now + timedelta(minutes=10)).isoformat(),
            "status":      "PENDING",
        }, default=str)
        await redis_client.set(f"suggestion:{s.id}", payload, ex=600)
        await redis_client.publish(CHANNELS["new_suggestion"], payload)

        logger.success(
            f"NEW SUGGESTION: {suggestion.get('symbol')} {suggestion.get('direction')} "
            f"score={suggestion.get('confidence_score')} id={s.id}"
        )
        return s.id

    except Exception as e:
        logger.error(f"Failed to save suggestion: {e}")
        return None

"""
APScheduler orchestrator for the AI Trading Intelligence Platform.

Schedule (all times IST / Asia/Kolkata):
  08:45  pre_market_research   — global data, FII/DII, market structure
  09:15  scan_cycle_start      — starts 90-second scan loop
  09:16+ scan_cycle            — runs every 90 s while market is open
  15:15  pre_squareoff_alert   — warns user to close positions
  15:25  auto_squareoff        — closes all MIS positions
  15:30  post_market_close     — records daily P&L, stops scan loop
  Sat    weekly_learning       — ML self-evaluation at 16:00
"""

import asyncio
import json
from datetime import datetime, timezone, date
from loguru import logger

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import settings
from backend.redis_client import redis_client, CHANNELS, KEYS
from backend.broker.orders import order_manager
from backend.routers.agents_status import update_agent

_scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
_scan_loop_running = False
_nifty_token: int | None = None


# ─── Market open check ────────────────────────────────────────────────────────

def _is_market_open() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:   # Saturday=5, Sunday=6
        return False
    t = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= t <= 15 * 60 + 25


# ─── Job 1: Pre-market research (8:45 AM) ────────────────────────────────────

async def pre_market_research():
    logger.info("═" * 50)
    logger.info("PRE-MARKET RESEARCH STARTING (8:45 AM)")

    update_agent("global_macro_agent", "ACTIVE", "Fetching global markets...")

    try:
        from backend.web_research.global_data import global_data_fetcher
        global_data = await global_data_fetcher.fetch_all()
        context = global_data_fetcher.interpret_global_context(global_data)

        await redis_client.set(
            "morning:global_data",
            json.dumps({"data": global_data, "context": context, "ts": datetime.now(timezone.utc).isoformat()}),
            ex=3600 * 4,
        )
        update_agent("global_macro_agent", "WAITING", f"Global: {context.get('overall_bias', 'NEUTRAL')}")
        logger.info(f"Global data fetched. Bias: {context.get('overall_bias', '?')}")
    except Exception as e:
        logger.error(f"Global data fetch failed: {e}")
        update_agent("global_macro_agent", "ERROR", str(e)[:80])

    try:
        from backend.web_research.nse_scraper import nse_scraper
        fii_dii = await nse_scraper.get_fii_dii_data()
        if fii_dii:
            await redis_client.set("morning:fii_dii", json.dumps(fii_dii), ex=3600 * 4)
        update_agent("fii_dii_agent", "WAITING", f"FII net: {fii_dii.get('fii_net', '?') if fii_dii else 'n/a'}")
        logger.info("FII/DII data fetched.")
    except Exception as e:
        logger.warning(f"FII/DII fetch failed: {e}")

    try:
        from backend.web_research.news_fetcher import news_fetcher
        await news_fetcher.fetch_all()
        update_agent("news_intelligence_agent", "WAITING", "News loaded")
        logger.info("News fetched.")
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")

    try:
        from backend.web_research.economic_calendar import economic_calendar
        calendar = await economic_calendar.get_today_events()
        await redis_client.set("morning:calendar", json.dumps(calendar or []), ex=3600 * 4)
        logger.info("Economic calendar loaded.")
    except Exception as e:
        logger.warning(f"Economic calendar failed: {e}")

    logger.info("Pre-market research complete.")


# ─── Job 2: Morning brief + regime detection (9:00 AM) ───────────────────────

async def morning_brief():
    """Compute and publish the final morning brief at 9:00 AM."""
    logger.info("MORNING BRIEF COMPUTATION (9:00 AM)")
    update_agent("market_regime_agent", "ACTIVE", "Computing regime from overnight data...")

    try:
        # Try to get Nifty candles for regime computation
        global _nifty_token
        loop = asyncio.get_event_loop()
        from backend.pipeline import _get_token, _fetch_candles

        if not _nifty_token:
            _nifty_token = await loop.run_in_executor(None, _get_token, "NIFTY 50")
            if not _nifty_token:
                # Try alternative
                _nifty_token = await loop.run_in_executor(None, _get_token, "NIFTY")

        regime = "UNKNOWN"
        if _nifty_token:
            df_daily = await loop.run_in_executor(None, _fetch_candles, _nifty_token, "day", 60)
            df_15m   = await loop.run_in_executor(None, _fetch_candles, _nifty_token, "15minute", 3)

            if not df_daily.empty and not df_15m.empty:
                from backend.agents.market_intelligence.market_structure_agent import market_structure_agent
                ms = await loop.run_in_executor(
                    None, market_structure_agent.analyze,
                    df_15m, df_daily, df_15m,
                )
                regime = ms.get("regime", "UNKNOWN")
                logger.info(f"Regime detected: {regime}")

        await redis_client.set(KEYS["market_regime"], regime)
        update_agent("market_regime_agent", "WAITING", f"Regime: {regime}")

    except Exception as e:
        logger.error(f"Morning brief regime error: {e}")
        update_agent("market_regime_agent", "ERROR", str(e)[:80])

    logger.info("Morning brief ready.")


# ─── Job 3: Real-time scan cycle (every 90 s from 9:15 AM) ──────────────────

async def scan_cycle():
    """Full scan of all candidates → supervisor → save suggestions."""
    global _scan_loop_running
    if not _is_market_open():
        return
    if _scan_loop_running:
        logger.debug("Scan already running, skipping tick")
        return

    _scan_loop_running = True
    try:
        await _run_scan()
    finally:
        _scan_loop_running = False


async def _run_scan():
    update_agent("scanner_agent", "ACTIVE", "Scanning candidates...")

    # ── Gather shared context ────────────────────────────────────────────────
    macro_context:  dict = {}
    news_context:   dict = {}
    sector_context: dict = {}
    global_context: dict = {}
    options_data:   dict = {}

    try:
        raw = await redis_client.get("morning:global_data")
        if raw:
            data = json.loads(raw)
            global_context = data.get("context", {})
            macro_context  = data.get("data", {})
    except Exception:
        pass

    # ── Get market regime ────────────────────────────────────────────────────
    regime_raw = await redis_client.get(KEYS["market_regime"])
    market_regime = regime_raw if regime_raw else "UNKNOWN"

    # ── Get portfolio state ──────────────────────────────────────────────────
    portfolio_state = {"open_positions_count": 0, "total_exposure_pct": 0}
    try:
        from backend.broker.position_monitor import position_monitor
        open_positions = position_monitor.get_all_positions()
        portfolio_state["open_positions_count"] = len(open_positions)
        if open_positions:
            total_exposure = sum(
                abs(p.get("entry_price", 0) * p.get("quantity", 0))
                for p in open_positions
            )
            portfolio_state["total_exposure_pct"] = round(total_exposure / settings.capital * 100, 1)
    except Exception:
        pass

    if portfolio_state["open_positions_count"] >= settings.max_open_positions:
        update_agent("scanner_agent", "WAITING",
                     f"Max positions open ({settings.max_open_positions}). Scan paused.")
        return

    # ── Check trading not disabled ───────────────────────────────────────────
    disabled = await redis_client.get("trading:disabled_today")
    if disabled:
        update_agent("scanner_agent", "SLEEP", "Trading disabled today (daily limit hit).")
        return

    # ── Get daily realized P&L ───────────────────────────────────────────────
    today = date.today().isoformat()
    daily_pnl_raw = await redis_client.get(f"daily:realized_pnl:{today}")
    daily_pnl = float(daily_pnl_raw or 0)

    # ── Run scanner ──────────────────────────────────────────────────────────
    try:
        from backend.agents.execution_intelligence.scanner_agent import scanner_agent
        sector_perf: dict[str, float] = {}  # populated from sector rotation agent in production
        candidates = await scanner_agent.scan(
            sector_performance=sector_perf,
            market_regime=market_regime,
        )
        update_agent("scanner_agent", "WAITING",
                     f"{len(candidates)} candidates found in regime {market_regime}")
        await redis_client.set(
            "scanner:candidates",
            json.dumps({"candidates": candidates, "scanned_at": datetime.now(timezone.utc).isoformat()}),
            ex=300,
        )
    except Exception as e:
        logger.error(f"Scanner error: {e}")
        update_agent("scanner_agent", "ERROR", str(e)[:80])
        return

    if not candidates:
        logger.info("No scanner candidates this cycle.")
        return

    # ── Get existing pending suggestions to avoid duplicates ─────────────────
    existing_symbols: set[str] = set()
    try:
        existing_raw = await redis_client.keys("suggestion:*")
        for key in (existing_raw or []):
            raw = await redis_client.get(key)
            if raw:
                d = json.loads(raw)
                if d.get("status", "PENDING") == "PENDING":
                    existing_symbols.add(d.get("symbol", ""))
    except Exception:
        pass

    # ── Analyse top candidates ────────────────────────────────────────────────
    from backend.pipeline import analyze_symbol, save_suggestion
    from backend.database import get_db_session

    suggestions_this_cycle = 0

    for candidate in candidates[:5]:  # analyse top 5 only to control Claude cost
        sym = candidate["symbol"]
        ltp = candidate["ltp"]

        if sym in existing_symbols:
            logger.debug(f"Skipping {sym} — already has pending suggestion")
            continue

        logger.info(f"Analysing {sym} @ ₹{ltp:.2f} (pre_score={candidate['pre_score']:.1f})")

        suggestion = await analyze_symbol(
            symbol=sym,
            ltp=ltp,
            market_regime=market_regime,
            macro_context=macro_context,
            news_context=news_context,
            sector_context=sector_context,
            global_context=global_context,
            options_data=options_data,
            portfolio_state=portfolio_state,
            daily_pnl=daily_pnl,
            nifty_token=_nifty_token,
        )

        if suggestion:
            async with get_db_session() as db:
                suggestion_id = await save_suggestion(suggestion, db)
            if suggestion_id:
                suggestions_this_cycle += 1
                existing_symbols.add(sym)

    logger.info(f"Scan cycle complete. {suggestions_this_cycle} suggestion(s) fired.")


# ─── Job 4: Pre square-off alert (3:15 PM) ───────────────────────────────────

async def pre_squareoff_alert():
    logger.warning("⚠️  3:15 PM — 10 minutes to auto square-off!")
    await redis_client.publish(CHANNELS["squareoff_alert"], json.dumps({
        "message": "10 minutes to auto square-off at 3:25 PM. Review open positions.",
        "time": "15:15",
    }))


# ─── Job 5: Auto square-off (3:25 PM) ───────────────────────────────────────

async def auto_squareoff():
    logger.warning("AUTO SQUARE-OFF (3:25 PM)")
    update_agent("execution_agent", "ACTIVE", "Auto square-off all MIS positions")

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, order_manager.squareoff_all_positions)
        logger.info("Auto square-off complete.")
        update_agent("execution_agent", "WAITING", "Square-off complete")
        await redis_client.publish(CHANNELS["squareoff_alert"], json.dumps({
            "message": "Auto square-off executed at 3:25 PM.",
            "time": "15:25",
        }))
    except Exception as e:
        logger.error(f"Auto square-off error: {e}")
        update_agent("execution_agent", "ERROR", str(e)[:80])


# ─── Job 6: Post-market close (3:30 PM) ──────────────────────────────────────

async def post_market_close():
    logger.info("POST-MARKET CLOSE (3:30 PM)")

    # Record today's P&L
    try:
        from backend.broker.kite_auth import kite_session
        if kite_session.is_connected():
            positions = kite_session.get_positions()
            realized = sum(
                float(p.get("realised", 0))
                for p in positions.get("day", [])
                if p.get("product") == "MIS"
            )
            today = date.today().isoformat()
            await redis_client.set(f"daily:realized_pnl:{today}", str(realized), ex=86400 * 7)
            logger.info(f"Today's realized P&L: ₹{realized:,.0f}")
    except Exception as e:
        logger.warning(f"P&L recording failed: {e}")

    update_agent("performance_analytics_agent", "WAITING",
                 "Daily P&L recorded. Session complete.")
    logger.info("Post-market tasks complete.")


# ─── Job 7: Weekly ML self-evaluation (Saturday 4 PM) ────────────────────────

async def weekly_learning():
    logger.info("WEEKLY ML SELF-EVALUATION (Saturday 4:00 PM)")
    update_agent("learning_agent", "ACTIVE", "Running weekly self-evaluation...")

    try:
        from backend.agents.risk_and_learning.ml_self_evaluation_agent import ml_self_evaluation_agent
        from backend.database import get_db_session
        from backend.models import Trade
        from sqlalchemy import select
        from datetime import timedelta

        async with get_db_session() as db:
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            result = await db.execute(
                select(Trade).where(Trade.entry_time >= seven_days_ago)
            )
            trades_orm = result.scalars().all()
            trades = [
                {
                    "r_multiple":     t.r_multiple,
                    "net_pnl":        t.net_pnl,
                    "strategy_name":  t.strategy_name,
                    "confidence_score": t.confidence_score,
                    "entry_time":     t.entry_time,
                    "regime":         getattr(t, "regime", "UNKNOWN"),
                }
                for t in trades_orm
            ]

        if len(trades) < 3:
            logger.info("Not enough trades for weekly review.")
            update_agent("learning_agent", "SLEEP", "< 3 trades this week — review skipped")
            return

        review = await asyncio.get_event_loop().run_in_executor(
            None, ml_self_evaluation_agent.weekly_review, trades, []
        )

        await redis_client.set(
            "learning:weekly_review",
            json.dumps({**review, "generated_at": datetime.now(timezone.utc).isoformat()}),
            ex=86400 * 7,
        )
        update_agent("learning_agent", "SLEEP",
                     f"Review done. WR={review['week_stats'].get('win_rate', 0):.0%} "
                     f"exp={review['week_stats'].get('expectancy', 0):+.2f}R")
        logger.info("Weekly ML review complete.")

    except Exception as e:
        logger.error(f"Weekly learning error: {e}")
        update_agent("learning_agent", "ERROR", str(e)[:80])


# ─── Scheduler setup ──────────────────────────────────────────────────────────

def start_scheduler():
    tz = "Asia/Kolkata"

    # Pre-market research at 8:45 AM on weekdays
    _scheduler.add_job(
        pre_market_research, CronTrigger(hour=8, minute=45, day_of_week="mon-fri", timezone=tz),
        id="pre_market", name="Pre-Market Research", replace_existing=True,
    )

    # Morning brief / regime detection at 9:00 AM
    _scheduler.add_job(
        morning_brief, CronTrigger(hour=9, minute=0, day_of_week="mon-fri", timezone=tz),
        id="morning_brief", name="Morning Brief", replace_existing=True,
    )

    # Real-time scan every 90 seconds from 9:16 AM
    _scheduler.add_job(
        scan_cycle, "interval", seconds=90,
        start_date=datetime.now().replace(hour=9, minute=16, second=0, microsecond=0),
        id="scan_cycle", name="Real-Time Scan Cycle", replace_existing=True,
    )

    # Pre square-off alert at 3:15 PM
    _scheduler.add_job(
        pre_squareoff_alert, CronTrigger(hour=15, minute=15, day_of_week="mon-fri", timezone=tz),
        id="pre_squareoff", name="Pre Square-off Alert", replace_existing=True,
    )

    # Auto square-off at 3:25 PM
    _scheduler.add_job(
        auto_squareoff, CronTrigger(hour=15, minute=25, day_of_week="mon-fri", timezone=tz),
        id="auto_squareoff", name="Auto Square-off", replace_existing=True,
    )

    # Post-market at 3:30 PM
    _scheduler.add_job(
        post_market_close, CronTrigger(hour=15, minute=30, day_of_week="mon-fri", timezone=tz),
        id="post_market", name="Post-Market Close", replace_existing=True,
    )

    # Weekly ML review every Saturday at 4:00 PM
    _scheduler.add_job(
        weekly_learning, CronTrigger(hour=16, minute=0, day_of_week="sat", timezone=tz),
        id="weekly_learning", name="Weekly ML Self-Evaluation", replace_existing=True,
    )

    _scheduler.start()

    jobs = [j.name for j in _scheduler.get_jobs()]
    logger.info(f"Scheduler started with {len(jobs)} jobs: {jobs}")


def shutdown_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")

"""
No-Trade Protocol — defines conditions when the system should NOT suggest any trades.
Called before every suggestion cycle.
"""

from datetime import datetime, time, date
from loguru import logger
from backend.config import settings
from backend.redis_client import redis_client


# Indian stock exchange holidays (NSE/BSE) - update annually
NSE_HOLIDAYS_2025 = {
    date(2025, 1, 26),   # Republic Day
    date(2025, 2, 26),   # Mahashivratri
    date(2025, 3, 14),   # Holi
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 24),  # Dussehra
    date(2025, 11, 5),   # Diwali
    date(2025, 12, 25),  # Christmas
}

NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 19),   # Holi
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 11, 12),  # Diwali
    date(2026, 12, 25),  # Christmas
}

ALL_HOLIDAYS = NSE_HOLIDAYS_2025 | NSE_HOLIDAYS_2026


class NoTradeProtocol:
    """
    Returns no_trade=True with reason when trading should be blocked.
    These are HARD STOPS — the system will not produce suggestions.
    """

    async def check(
        self,
        daily_pnl: float,
        weekly_pnl: float,
        vix: float,
        open_positions_count: int,
        market_halted: bool = False,
    ) -> dict:
        now = datetime.now()
        today = now.date()
        current_time = now.time()

        result = {
            "no_trade": False,
            "reason": "",
            "severity": "INFO",
            "resume_at": None,
        }

        # ── Market closed ──────────────────────────────────────────────────
        if today.weekday() >= 5:  # Saturday=5, Sunday=6
            result["no_trade"] = True
            result["reason"] = "Market closed: weekend"
            result["severity"] = "INFO"
            return result

        if today in ALL_HOLIDAYS:
            result["no_trade"] = True
            result["reason"] = f"NSE Holiday: {today}"
            result["severity"] = "INFO"
            return result

        # ── Pre-market / post-market ──────────────────────────────────────
        market_open = time(9, 15)
        market_close = time(15, 30)
        squareoff = time(15, 25)

        if current_time < market_open:
            result["no_trade"] = True
            result["reason"] = "Market not yet open (opens 9:15 AM)"
            result["resume_at"] = "09:15"
            return result

        if current_time >= market_close:
            result["no_trade"] = True
            result["reason"] = "Market closed for the day"
            result["severity"] = "INFO"
            return result

        # ── No-trade buffer (9:15–9:20 AM) ────────────────────────────────
        buffer_end = time(9, 15 + settings.no_trade_buffer_minutes)
        if current_time < buffer_end:
            result["no_trade"] = True
            result["reason"] = f"No-trade buffer: wait until {buffer_end.strftime('%H:%M')} for structure"
            result["resume_at"] = buffer_end.strftime("%H:%M")
            return result

        # ── Square-off time ────────────────────────────────────────────────
        if current_time >= squareoff:
            result["no_trade"] = True
            result["reason"] = "Past 3:25 PM — no new entries. Auto square-off time."
            result["severity"] = "WARNING"
            return result

        # ── Daily loss limit ───────────────────────────────────────────────
        if daily_pnl <= -settings.daily_loss_limit:
            result["no_trade"] = True
            result["reason"] = (
                f"Daily loss limit hit: ₹{daily_pnl:,.0f} loss "
                f"({abs(daily_pnl)/settings.capital*100:.1f}% of capital). "
                "Trading disabled for today. Come back tomorrow with a fresh mind."
            )
            result["severity"] = "CRITICAL"
            return result

        # ── Weekly loss limit ──────────────────────────────────────────────
        if weekly_pnl <= -settings.weekly_loss_limit:
            result["no_trade"] = True
            result["reason"] = (
                f"Weekly loss limit hit: ₹{weekly_pnl:,.0f} loss. "
                "Take a break. Review your journal. Come back next week."
            )
            result["severity"] = "CRITICAL"
            return result

        # ── VIX extreme (circuit breaker risk) ────────────────────────────
        if vix > 35:
            result["no_trade"] = True
            result["reason"] = f"India VIX = {vix:.1f} — EXTREME fear. Circuit breaker risk. No trading."
            result["severity"] = "CRITICAL"
            return result

        # ── Market halted ─────────────────────────────────────────────────
        if market_halted:
            result["no_trade"] = True
            result["reason"] = "Market halted (circuit breaker triggered)"
            result["severity"] = "CRITICAL"
            return result

        # ── Manual pause (from breaking news protocol) ────────────────────
        paused = await redis_client.get("suggestions:paused")
        if paused:
            result["no_trade"] = True
            result["reason"] = "Suggestions paused due to breaking news — will auto-resume in 5 min"
            result["severity"] = "WARNING"
            return result

        # ── Max positions already open ─────────────────────────────────────
        if open_positions_count >= settings.max_open_positions:
            result["no_trade"] = True
            result["reason"] = (
                f"Max {settings.max_open_positions} positions already open. "
                "Wait for one to close before new entries."
            )
            result["severity"] = "WARNING"
            return result

        return result


no_trade_protocol = NoTradeProtocol()

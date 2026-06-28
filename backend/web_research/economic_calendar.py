"""
Economic Calendar — parses key India and global economic events.
High-impact events trigger risk reduction.
"""

import httpx
from datetime import datetime, date
from loguru import logger


INDIA_EVENTS_KEYWORDS = [
    "RBI", "monetary policy", "CPI", "WPI", "GDP", "IIP",
    "budget", "trade deficit", "FII", "rupee", "inflation",
    "Nifty", "BSE", "NSE", "SEBI"
]

HIGH_IMPACT_KEYWORDS = ["RBI rate", "budget", "GDP", "CPI data", "election result"]


class EconomicCalendar:

    async def get_today_events(self) -> list[dict]:
        """
        Returns today's economic events from a simple hardcoded calendar
        + Investing.com economic calendar API (free tier).
        """
        events = []

        # Static high-impact recurring events
        today = datetime.now()
        month = today.month
        day = today.day

        # RBI MPC meetings (typically every 2 months: Feb, Apr, Jun, Aug, Oct, Dec)
        if month in [2, 4, 6, 8, 10, 12] and day in [7, 8, 9]:
            events.append({
                "time": "10:00",
                "event": "RBI Monetary Policy Committee Decision",
                "country": "India",
                "impact": "HIGH",
                "description": "Interest rate decision by RBI. Nifty/Bank Nifty very volatile around this.",
            })

        # Try Investing.com calendar (scrape)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                today_str = today.strftime("%Y-%m-%d")
                resp = await client.get(
                    "https://api.investing.com/api/financialdata/economic-calendars",
                    params={"dateFrom": today_str, "dateTo": today_str, "countries": "14,5"},  # India, USA
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", [])[:10]:
                        impact = item.get("importance", 1)
                        events.append({
                            "time": item.get("time", ""),
                            "event": item.get("event", ""),
                            "country": item.get("countryName", ""),
                            "impact": "HIGH" if impact == 3 else "MEDIUM" if impact == 2 else "LOW",
                            "actual": item.get("actual", ""),
                            "forecast": item.get("forecast", ""),
                            "previous": item.get("previous", ""),
                        })
        except Exception:
            pass  # Calendar API may not be accessible, continue with static events

        logger.info(f"Economic calendar: {len(events)} events today")
        return events

    def has_high_impact_event(self, events: list[dict]) -> bool:
        return any(e.get("impact") == "HIGH" for e in events)

    def format_for_prompt(self, events: list[dict]) -> str:
        if not events:
            return "No major economic events today."
        lines = []
        for e in events:
            lines.append(f"• {e.get('time', 'TBD')} — {e.get('event', '')} [{e.get('impact', 'LOW')} impact]")
        return "\n".join(lines)


economic_calendar = EconomicCalendar()

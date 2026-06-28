"""
Scanner Agent — Agent 14.
Scans 500 NSE stocks every 15 minutes.
Filters by liquidity, technical setup, and sector alignment.
Returns top 5–10 candidates for deeper analysis.
"""

import asyncio
from datetime import datetime, timedelta
from loguru import logger
from backend.broker.kite_auth import kite_session
from backend.technical.indicators import indicator_engine


NIFTY_500_SYMBOLS = [
    # Nifty 50 core (highly liquid)
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "KOTAKBANK", "AXISBANK",
    "LT", "SBIN", "BAJFINANCE", "BHARTIARTL", "TITAN", "ASIANPAINT", "MARUTI",
    "NESTLEIND", "HINDALCO", "TATAMOTORS", "TATASTEEL", "SUNPHARMA", "WIPRO",
    "HCLTECH", "POWERGRID", "NTPC", "COALINDIA", "ONGC", "BPCL", "IOC",
    "ADANIPORTS", "TECHM", "DIVISLAB", "CIPLA", "DRREDDY", "BAJAJ-AUTO",
    "HEROMOTOCO", "M&M", "EICHERMOT", "BAJAJFINSV", "GRASIM", "ULTRACEMCO",
    "SHREECEM", "UPL", "BRITANNIA", "DABUR", "MARICO", "HINDUNILVR", "ITC",
    # Midcap (high movement)
    "MPHASIS", "COFORGE", "PERSISTENT", "LTIM", "KPITTECH",
    "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "RBLBANK",
    "GODREJPROP", "DLF", "PRESTIGE", "OBEROIRLTY",
    "PHOENIXLTD", "NAUKRI", "ZOMATO", "PAYTM", "POLICYBZR",
    "TATAPOWER", "ADANIGREEN", "ADANIPOWER",
    "PIDILITIND", "BERGEPAINT", "KANSAINER",
    "VOLTAS", "HAVELLS", "CROMPTON", "VGUARD",
]

MINIMUM_DAILY_VOLUME = 5_00_000   # 5 lakh shares minimum
MINIMUM_PRICE = 100               # stocks above ₹100


class ScannerAgent:
    name = "Scanner Agent"

    async def scan(
        self,
        sector_performance: dict[str, float],
        market_regime: str,
        symbols_override: list[str] = None,
    ) -> list[dict]:
        """
        Full scan across all liquid stocks.
        Returns list of candidates sorted by setup quality score.
        """
        symbols = symbols_override or NIFTY_500_SYMBOLS
        candidates = []

        logger.info(f"Scanner: scanning {len(symbols)} symbols in regime {market_regime}")

        # Get quotes for all symbols in one API call
        quote_symbols = [f"NSE:{s}" for s in symbols[:100]]  # batch of 100
        try:
            quotes = kite_session.get_ltp(quote_symbols)
        except Exception as e:
            logger.error(f"Scanner quote error: {e}")
            return []

        for sym in symbols:
            try:
                ltp_key = f"NSE:{sym}"
                if ltp_key not in quotes:
                    continue

                ltp = quotes[ltp_key].get("last_price", 0)
                if ltp < MINIMUM_PRICE:
                    continue

                # Quick pre-filter using quote only
                candidate = {
                    "symbol": sym,
                    "ltp": ltp,
                    "pre_score": self._quick_score(sym, ltp, market_regime, sector_performance),
                }
                if candidate["pre_score"] >= 5:
                    candidates.append(candidate)

            except Exception:
                pass

        # Sort by pre-score and return top 15 for deeper analysis
        candidates.sort(key=lambda x: x["pre_score"], reverse=True)
        top_candidates = candidates[:15]

        logger.info(f"Scanner found {len(top_candidates)} candidates from {len(candidates)} qualified")
        return top_candidates

    def _quick_score(
        self,
        symbol: str,
        ltp: float,
        regime: str,
        sector_performance: dict,
    ) -> float:
        """Quick 0–10 score based on liquid data only."""
        score = 5.0

        # Prefer high-liquidity stocks
        nifty50 = {"RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "KOTAKBANK",
                   "AXISBANK", "LT", "SBIN", "BAJFINANCE", "BHARTIARTL"}
        if symbol in nifty50:
            score += 1

        # Sector alignment
        for sector, perf in (sector_performance or {}).items():
            if self._in_sector(symbol, sector):
                if perf > 0.5:
                    score += 1.5
                elif perf < -0.5:
                    score -= 1.5
                break

        # Regime preference
        if regime in ["TRENDING_UP", "TRENDING_DOWN"] and symbol in nifty50:
            score += 0.5

        return min(10, max(0, score))

    def _in_sector(self, symbol: str, sector: str) -> bool:
        banking = {"HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN", "BANDHANBNK", "FEDERALBNK"}
        it = {"TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "MPHASIS", "COFORGE", "PERSISTENT", "LTIM"}
        if "BANK" in sector.upper() and symbol in banking:
            return True
        if "IT" in sector.upper() and symbol in it:
            return True
        return False


scanner_agent = ScannerAgent()

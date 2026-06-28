"""
NSE data scraper — fetches FII/DII data, corporate actions, economic calendar.
Uses NSE's public API endpoints (no auth required for public data).
"""

import httpx
from datetime import datetime, timedelta
from loguru import logger


NSE_BASE = "https://www.nseindia.com"
NSE_API = "https://www.nseindia.com/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


class NSEScraper:

    def __init__(self):
        self._client = httpx.AsyncClient(
            headers=HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )
        self._session_established = False

    async def _establish_session(self):
        """NSE requires visiting homepage first to get cookies."""
        if not self._session_established:
            try:
                await self._client.get(NSE_BASE)
                self._session_established = True
            except Exception as e:
                logger.warning(f"NSE session setup failed: {e}")

    async def get_fii_dii_data(self) -> dict:
        """Fetch FII/DII activity for today."""
        await self._establish_session()
        try:
            today = datetime.now().strftime("%d-%m-%Y")
            resp = await self._client.get(f"{NSE_API}/fiidiiTradeReact?type=fiidii&date={today}")
            data = resp.json()

            fii_net = 0
            dii_net = 0

            if isinstance(data, list):
                for item in data:
                    if "FII/FPI" in str(item.get("category", "")):
                        fii_net = float(item.get("netVal", 0))
                    elif "DII" in str(item.get("category", "")):
                        dii_net = float(item.get("netVal", 0))

            return {
                "fii_net": fii_net,
                "dii_net": dii_net,
                "date": today,
                "fii_bias": "BUY" if fii_net > 0 else "SELL",
                "dii_bias": "BUY" if dii_net > 0 else "SELL",
                "combined": fii_net + dii_net,
            }
        except Exception as e:
            logger.error(f"NSE FII/DII fetch error: {e}")
            return {"fii_net": 0, "dii_net": 0, "date": "", "fii_bias": "UNKNOWN", "dii_bias": "UNKNOWN", "combined": 0}

    async def get_options_chain(self, symbol: str = "NIFTY") -> dict:
        """Fetch NSE options chain for PCR calculation."""
        await self._establish_session()
        try:
            resp = await self._client.get(f"{NSE_API}/option-chain-indices?symbol={symbol}")
            data = resp.json()

            records = data.get("records", {})
            data_records = records.get("data", [])

            total_ce_oi = sum(r.get("CE", {}).get("openInterest", 0) for r in data_records if r.get("CE"))
            total_pe_oi = sum(r.get("PE", {}).get("openInterest", 0) for r in data_records if r.get("PE"))

            pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
            max_pain = self._calculate_max_pain(data_records)

            return {
                "symbol": symbol,
                "total_ce_oi": total_ce_oi,
                "total_pe_oi": total_pe_oi,
                "pcr": round(pcr, 2),
                "max_pain": max_pain,
                "pcr_bias": "BULLISH" if pcr > 1.0 else "BEARISH" if pcr < 0.8 else "NEUTRAL",
            }
        except Exception as e:
            logger.error(f"NSE options chain error ({symbol}): {e}")
            return {"symbol": symbol, "pcr": 1.0, "max_pain": 0, "pcr_bias": "NEUTRAL"}

    def _calculate_max_pain(self, data_records: list) -> float:
        """Max pain = strike where total option sellers lose the least."""
        strikes = {}
        for r in data_records:
            strike = r.get("strikePrice", 0)
            if not strike:
                continue
            strikes[strike] = {
                "ce_oi": r.get("CE", {}).get("openInterest", 0),
                "pe_oi": r.get("PE", {}).get("openInterest", 0),
            }

        if not strikes:
            return 0

        max_pain_strike = None
        min_pain = float("inf")

        for test_strike in strikes:
            total_pain = 0
            for s, data in strikes.items():
                ce_pain = max(0, test_strike - s) * data["ce_oi"]
                pe_pain = max(0, s - test_strike) * data["pe_oi"]
                total_pain += ce_pain + pe_pain
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = test_strike

        return max_pain_strike or 0

    async def get_circuit_breakers(self) -> list[dict]:
        """Stocks hitting upper/lower circuit — avoid trading these."""
        await self._establish_session()
        try:
            resp = await self._client.get(f"{NSE_API}/live-analysis-data?index=securities52WeekHighLow")
            data = resp.json()
            return data.get("data", [])[:20]
        except Exception:
            return []

    async def get_corporate_actions(self, symbol: str = None) -> list[dict]:
        """Corporate actions calendar (dividends, splits, bonus, results)."""
        await self._establish_session()
        try:
            url = f"{NSE_API}/corporates-corporateActions?index=equities"
            if symbol:
                url += f"&symbol={symbol}"
            resp = await self._client.get(url)
            data = resp.json()
            return data[:20] if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"NSE corporate actions error: {e}")
            return []

    async def close(self):
        await self._client.aclose()


nse_scraper = NSEScraper()

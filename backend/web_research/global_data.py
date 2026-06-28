"""
Global market data via yfinance.
Fetches S&P 500, NASDAQ, DXY, Crude, Gold, US 10Y yield, Nikkei, Hang Seng.
"""

import asyncio
from datetime import datetime, timedelta
from loguru import logger

try:
    import yfinance as yf
except ImportError:
    yf = None


GLOBAL_TICKERS = {
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
    "vix_us": "^VIX",
    "dxy": "DX-Y.NYB",
    "crude_wti": "CL=F",
    "crude_brent": "BZ=F",
    "gold": "GC=F",
    "us_10y_yield": "^TNX",
    "nikkei": "^N225",
    "hang_seng": "^HSI",
    "sgx_nifty": "^NSEI",     # approximate — SGX Nifty not on yfinance directly
    "bitcoin": "BTC-USD",
    "india_vix": "^INDIAVIX",
    "nifty": "^NSEI",
    "banknifty": "^NSEBANK",
    "sensex": "^BSESN",
}


class GlobalDataFetcher:

    async def fetch_all(self) -> dict:
        """Fetch latest data for all global tickers asynchronously."""
        if yf is None:
            logger.error("yfinance not installed")
            return {}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync)

    def _fetch_sync(self) -> dict:
        results = {}
        tickers_str = " ".join(GLOBAL_TICKERS.values())
        try:
            data = yf.download(tickers_str, period="2d", interval="1d", progress=False, group_by="ticker")
        except Exception as e:
            logger.error(f"yfinance batch download error: {e}")
            return {}

        for name, ticker in GLOBAL_TICKERS.items():
            try:
                if ticker in data.columns:
                    series = data[ticker]["Close"]
                else:
                    series = data["Close"] if len(GLOBAL_TICKERS) == 1 else None

                if series is None or len(series) < 1:
                    continue

                latest = float(series.iloc[-1])
                prev = float(series.iloc[-2]) if len(series) > 1 else latest
                change_pct = ((latest - prev) / prev * 100) if prev else 0

                results[name] = {
                    "ticker": ticker,
                    "price": round(latest, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev, 2),
                    "direction": "UP" if change_pct > 0 else "DOWN" if change_pct < 0 else "FLAT",
                }
            except Exception:
                pass

        logger.info(f"Global data fetched: {len(results)} instruments")
        return results

    def interpret_global_context(self, data: dict) -> dict:
        """
        Derive India market implication from global data.
        """
        implications = []
        bias_score = 0  # positive = bullish for India

        sp500 = data.get("sp500", {})
        if sp500.get("change_pct", 0) > 0.5:
            implications.append(f"S&P 500 +{sp500['change_pct']:.1f}% overnight — POSITIVE for India open")
            bias_score += 2
        elif sp500.get("change_pct", 0) < -0.5:
            implications.append(f"S&P 500 {sp500['change_pct']:.1f}% — NEGATIVE for India open")
            bias_score -= 2

        vix = data.get("vix_us", {})
        if vix.get("price", 20) < 15:
            implications.append(f"US VIX {vix.get('price', 0):.1f} — very calm, risk-on environment")
            bias_score += 1
        elif vix.get("price", 20) > 25:
            implications.append(f"US VIX {vix.get('price', 0):.1f} — elevated fear, risk-off")
            bias_score -= 2

        dxy = data.get("dxy", {})
        if dxy.get("change_pct", 0) > 0.3:
            implications.append(f"DXY +{dxy['change_pct']:.2f}% — dollar strength may weigh on FII flows")
            bias_score -= 1
        elif dxy.get("change_pct", 0) < -0.3:
            implications.append(f"DXY {dxy['change_pct']:.2f}% — dollar weakness, good for emerging markets")
            bias_score += 1

        crude = data.get("crude_wti", {})
        if crude.get("change_pct", 0) > 2:
            implications.append(f"Crude +{crude['change_pct']:.1f}% — NEGATIVE for India (import cost)")
            bias_score -= 1

        nikkei = data.get("nikkei", {})
        if nikkei.get("change_pct", 0) > 1:
            implications.append(f"Nikkei +{nikkei['change_pct']:.1f}% — positive Asia signal")
            bias_score += 1
        elif nikkei.get("change_pct", 0) < -1:
            implications.append(f"Nikkei {nikkei['change_pct']:.1f}% — weak Asia signal")
            bias_score -= 1

        overall_bias = "BULLISH" if bias_score >= 2 else "BEARISH" if bias_score <= -2 else "NEUTRAL"

        return {
            "bias_score": bias_score,
            "overall_bias": overall_bias,
            "implications": implications,
            "summary": f"Global context: {overall_bias} for India. Score: {bias_score:+d}",
        }


global_data_fetcher = GlobalDataFetcher()

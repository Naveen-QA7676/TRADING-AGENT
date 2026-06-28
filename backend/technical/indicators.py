"""
Complete technical indicator engine.
19 indicators across 5 timeframes (1m, 5m, 15m, 1H, Daily).
Uses pandas-ta for standard indicators + custom implementations for advanced ones.
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class IndicatorResult:
    """Single indicator reading with signal interpretation."""
    name: str
    value: float | str | None
    signal: str           # "BUY", "SELL", "NEUTRAL"
    strength: float       # 0.0 – 1.0
    description: str      # human-readable reason


@dataclass
class MultiTFIndicators:
    """All indicator results for a single timeframe."""
    timeframe: str
    rsi: Optional[IndicatorResult] = None
    macd: Optional[IndicatorResult] = None
    ema_20: Optional[IndicatorResult] = None
    ema_50: Optional[IndicatorResult] = None
    ema_200: Optional[IndicatorResult] = None
    vwap: Optional[IndicatorResult] = None
    bollinger: Optional[IndicatorResult] = None
    atr: Optional[IndicatorResult] = None
    adx: Optional[IndicatorResult] = None
    supertrend: Optional[IndicatorResult] = None
    stoch_rsi: Optional[IndicatorResult] = None
    obv: Optional[IndicatorResult] = None
    cci: Optional[IndicatorResult] = None
    mfi: Optional[IndicatorResult] = None
    ichimoku: Optional[IndicatorResult] = None
    pivot_points: Optional[dict] = None
    overall_signal: str = "NEUTRAL"
    buy_count: int = 0
    sell_count: int = 0
    neutral_count: int = 0
    bull_score: float = 0.0    # 0–100


class IndicatorEngine:
    """
    Computes all 19 indicators on a DataFrame of OHLCV data.
    """

    # ── RSI ───────────────────────────────────────────────────────────────

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        df = df.copy()
        df.ta.rsi(length=period, append=True)
        col = f"RSI_{period}"
        if col not in df or df[col].isna().all():
            return IndicatorResult("RSI", None, "NEUTRAL", 0.5, "Insufficient data")

        val = df[col].iloc[-1]
        if val < 30:
            return IndicatorResult("RSI", round(val, 1), "BUY", 0.9, f"RSI {val:.1f} — oversold, bounce likely")
        elif val > 70:
            return IndicatorResult("RSI", round(val, 1), "SELL", 0.9, f"RSI {val:.1f} — overbought, pullback likely")
        elif 45 <= val <= 60:
            return IndicatorResult("RSI", round(val, 1), "BUY", 0.6, f"RSI {val:.1f} — bullish neutral zone")
        elif 40 <= val < 45:
            return IndicatorResult("RSI", round(val, 1), "NEUTRAL", 0.5, f"RSI {val:.1f} — neutral")
        else:
            return IndicatorResult("RSI", round(val, 1), "NEUTRAL", 0.5, f"RSI {val:.1f} — neutral zone")

    # ── MACD ──────────────────────────────────────────────────────────────

    @staticmethod
    def macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> IndicatorResult:
        df = df.copy()
        df.ta.macd(fast=fast, slow=slow, signal=signal, append=True)
        macd_col = f"MACD_{fast}_{slow}_{signal}"
        sig_col = f"MACDs_{fast}_{slow}_{signal}"
        hist_col = f"MACDh_{fast}_{slow}_{signal}"

        if macd_col not in df:
            return IndicatorResult("MACD", None, "NEUTRAL", 0.5, "Insufficient data")

        macd_val = df[macd_col].iloc[-1]
        sig_val = df[sig_col].iloc[-1]
        hist_val = df[hist_col].iloc[-1]
        prev_hist = df[hist_col].iloc[-2] if len(df) > 1 else hist_val

        if pd.isna(macd_val):
            return IndicatorResult("MACD", None, "NEUTRAL", 0.5, "Insufficient data")

        # Bullish crossover
        if macd_val > sig_val and prev_hist < 0 and hist_val > 0:
            return IndicatorResult("MACD", round(hist_val, 4), "BUY", 0.95,
                                   "MACD bullish crossover — strong entry signal")
        # Bearish crossover
        elif macd_val < sig_val and prev_hist > 0 and hist_val < 0:
            return IndicatorResult("MACD", round(hist_val, 4), "SELL", 0.95,
                                   "MACD bearish crossover — sell signal")
        # Histogram expanding positive
        elif hist_val > 0 and hist_val > prev_hist:
            return IndicatorResult("MACD", round(hist_val, 4), "BUY", 0.7,
                                   "MACD histogram growing — bullish momentum")
        # Histogram contracting (losing steam)
        elif hist_val > 0 and hist_val < prev_hist:
            return IndicatorResult("MACD", round(hist_val, 4), "NEUTRAL", 0.4,
                                   "MACD histogram shrinking — bullish momentum fading")
        elif hist_val < 0 and hist_val < prev_hist:
            return IndicatorResult("MACD", round(hist_val, 4), "SELL", 0.7,
                                   "MACD histogram growing negative — bearish momentum")
        else:
            return IndicatorResult("MACD", round(hist_val, 4), "NEUTRAL", 0.5, "MACD neutral")

    # ── EMAs ──────────────────────────────────────────────────────────────

    @staticmethod
    def ema(df: pd.DataFrame, period: int) -> IndicatorResult:
        close = df["close"]
        ema_val = close.ewm(span=period, adjust=False).mean().iloc[-1]
        ltp = close.iloc[-1]
        pct = ((ltp - ema_val) / ema_val) * 100

        if ltp > ema_val:
            strength = min(1.0, abs(pct) / 3.0)
            return IndicatorResult(f"EMA{period}", round(ema_val, 2), "BUY", strength,
                                   f"Price {pct:+.2f}% above EMA{period} — bullish")
        else:
            strength = min(1.0, abs(pct) / 3.0)
            return IndicatorResult(f"EMA{period}", round(ema_val, 2), "SELL", strength,
                                   f"Price {pct:+.2f}% below EMA{period} — bearish")

    @staticmethod
    def ema_stack(df: pd.DataFrame) -> IndicatorResult:
        """Check EMA alignment: EMA20 < EMA50 < price = bullish stack."""
        close = df["close"]
        e20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        e50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ltp = close.iloc[-1]

        if ltp > e20 > e50:
            return IndicatorResult("EMA_STACK", f"{e20:.2f}/{e50:.2f}", "BUY", 0.85,
                                   "Bullish EMA stack: Price > EMA20 > EMA50")
        elif ltp < e20 < e50:
            return IndicatorResult("EMA_STACK", f"{e20:.2f}/{e50:.2f}", "SELL", 0.85,
                                   "Bearish EMA stack: Price < EMA20 < EMA50")
        else:
            return IndicatorResult("EMA_STACK", f"{e20:.2f}/{e50:.2f}", "NEUTRAL", 0.4,
                                   "Mixed EMA alignment — choppy")

    # ── VWAP ──────────────────────────────────────────────────────────────

    @staticmethod
    def vwap(df: pd.DataFrame) -> IndicatorResult:
        """Session VWAP from intraday data."""
        df = df.copy()
        typical = (df["high"] + df["low"] + df["close"]) / 3
        vol = df["volume"]
        cum_tp_vol = (typical * vol).cumsum()
        cum_vol = vol.cumsum()
        vwap_series = cum_tp_vol / cum_vol

        vwap_val = vwap_series.iloc[-1]
        ltp = df["close"].iloc[-1]
        pct = ((ltp - vwap_val) / vwap_val) * 100

        if ltp > vwap_val:
            return IndicatorResult("VWAP", round(vwap_val, 2), "BUY", min(1.0, abs(pct)/1.5),
                                   f"Price {pct:+.2f}% above VWAP — bullish bias")
        else:
            return IndicatorResult("VWAP", round(vwap_val, 2), "SELL", min(1.0, abs(pct)/1.5),
                                   f"Price {pct:+.2f}% below VWAP — bearish bias")

    # ── Bollinger Bands ────────────────────────────────────────────────────

    @staticmethod
    def bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> IndicatorResult:
        df = df.copy()
        df.ta.bbands(length=period, std=std, append=True)
        upper_col = f"BBU_{period}_{std}"
        lower_col = f"BBL_{period}_{std}"
        mid_col = f"BBM_{period}_{std}"

        if upper_col not in df:
            return IndicatorResult("BB", None, "NEUTRAL", 0.5, "Insufficient data")

        upper = df[upper_col].iloc[-1]
        lower = df[lower_col].iloc[-1]
        mid = df[mid_col].iloc[-1]
        ltp = df["close"].iloc[-1]

        bandwidth = (upper - lower) / mid * 100
        pos = (ltp - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

        if ltp <= lower:
            return IndicatorResult("BB", f"{lower:.2f}/{upper:.2f}", "BUY", 0.9,
                                   "Price at lower BB — oversold bounce zone")
        elif ltp >= upper:
            return IndicatorResult("BB", f"{lower:.2f}/{upper:.2f}", "SELL", 0.9,
                                   "Price at upper BB — overbought")
        elif pos < 0.35:
            return IndicatorResult("BB", f"{lower:.2f}/{upper:.2f}", "BUY", 0.65,
                                   f"Price near lower BB (pos={pos:.1%}) — bullish tendency")
        elif pos > 0.65 and bandwidth > 2.0:
            return IndicatorResult("BB", f"{lower:.2f}/{upper:.2f}", "BUY", 0.6,
                                   "Price above midband with room — trending up")
        elif bandwidth < 1.0:
            return IndicatorResult("BB", f"{lower:.2f}/{upper:.2f}", "NEUTRAL", 0.3,
                                   f"BB squeeze (bw={bandwidth:.1f}%) — breakout pending")
        else:
            return IndicatorResult("BB", f"{lower:.2f}/{upper:.2f}", "NEUTRAL", 0.4,
                                   "BB midband — no clear directional signal")

    # ── ATR ───────────────────────────────────────────────────────────────

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        df = df.copy()
        df.ta.atr(length=period, append=True)
        col = f"ATRr_{period}"
        if col not in df:
            col = f"ATR_{period}"
        if col not in df:
            return IndicatorResult("ATR", None, "NEUTRAL", 0.5, "Insufficient data")

        atr_val = df[col].iloc[-1]
        ltp = df["close"].iloc[-1]
        atr_pct = (atr_val / ltp) * 100

        # Historical ATR average
        atr_avg = df[col].rolling(20).mean().iloc[-1]
        ratio = atr_val / atr_avg if atr_avg > 0 else 1.0

        if ratio > 1.5:
            desc = f"ATR {atr_val:.2f} ({atr_pct:.1f}%) — HIGH volatility (1.5× avg). Reduce size."
        elif ratio < 0.7:
            desc = f"ATR {atr_val:.2f} ({atr_pct:.1f}%) — LOW volatility. Breakout imminent?"
        else:
            desc = f"ATR {atr_val:.2f} ({atr_pct:.1f}%) — Normal volatility"

        return IndicatorResult("ATR", round(atr_val, 2), "NEUTRAL", 0.5, desc)

    # ── ADX ───────────────────────────────────────────────────────────────

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        df = df.copy()
        df.ta.adx(length=period, append=True)
        adx_col = f"ADX_{period}"
        dmp_col = f"DMP_{period}"
        dmn_col = f"DMN_{period}"

        if adx_col not in df:
            return IndicatorResult("ADX", None, "NEUTRAL", 0.5, "Insufficient data")

        adx_val = df[adx_col].iloc[-1]
        dmp = df[dmp_col].iloc[-1] if dmp_col in df else 0
        dmn = df[dmn_col].iloc[-1] if dmn_col in df else 0

        if adx_val >= 30:
            direction = "BUY" if dmp > dmn else "SELL"
            return IndicatorResult("ADX", round(adx_val, 1), direction, 0.85,
                                   f"ADX {adx_val:.0f} — strong trend. +DI={dmp:.0f} -DI={dmn:.0f}")
        elif adx_val >= 20:
            direction = "BUY" if dmp > dmn else "SELL"
            return IndicatorResult("ADX", round(adx_val, 1), direction, 0.6,
                                   f"ADX {adx_val:.0f} — moderate trend developing")
        else:
            return IndicatorResult("ADX", round(adx_val, 1), "NEUTRAL", 0.3,
                                   f"ADX {adx_val:.0f} — no clear trend (choppy)")

    # ── SuperTrend ────────────────────────────────────────────────────────

    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> IndicatorResult:
        df = df.copy()
        df.ta.supertrend(length=period, multiplier=multiplier, append=True)

        trend_col = f"SUPERTd_{period}_{multiplier}"
        if trend_col not in df:
            return IndicatorResult("SuperTrend", None, "NEUTRAL", 0.5, "Insufficient data")

        trend = df[trend_col].iloc[-1]
        ltp = df["close"].iloc[-1]

        if trend == 1:
            return IndicatorResult("SuperTrend", "BULLISH", "BUY", 0.85,
                                   "SuperTrend is BULLISH — green line below price")
        else:
            return IndicatorResult("SuperTrend", "BEARISH", "SELL", 0.85,
                                   "SuperTrend is BEARISH — red line above price")

    # ── Stochastic RSI ────────────────────────────────────────────────────

    @staticmethod
    def stoch_rsi(df: pd.DataFrame, rsi_len=14, stoch_len=14, k=3, d=3) -> IndicatorResult:
        df = df.copy()
        df.ta.stochrsi(length=rsi_len, rsi_length=stoch_len, k=k, d=d, append=True)
        k_col = f"STOCHRSIk_{rsi_len}_{stoch_len}_{k}_{d}"
        d_col = f"STOCHRSId_{rsi_len}_{stoch_len}_{k}_{d}"

        if k_col not in df:
            return IndicatorResult("StochRSI", None, "NEUTRAL", 0.5, "Insufficient data")

        k_val = df[k_col].iloc[-1]
        d_val = df[d_col].iloc[-1] if d_col in df else k_val
        prev_k = df[k_col].iloc[-2] if len(df) > 1 else k_val
        prev_d = df[d_col].iloc[-2] if (d_col in df and len(df) > 1) else d_val

        if k_val > d_val and prev_k <= prev_d and k_val < 20:
            return IndicatorResult("StochRSI", round(k_val, 1), "BUY", 0.95,
                                   f"StochRSI bullish crossover from oversold zone ({k_val:.0f})")
        elif k_val < d_val and prev_k >= prev_d and k_val > 80:
            return IndicatorResult("StochRSI", round(k_val, 1), "SELL", 0.95,
                                   f"StochRSI bearish crossover from overbought zone ({k_val:.0f})")
        elif k_val < 20:
            return IndicatorResult("StochRSI", round(k_val, 1), "BUY", 0.7,
                                   f"StochRSI oversold ({k_val:.0f}) — bounce zone")
        elif k_val > 80:
            return IndicatorResult("StochRSI", round(k_val, 1), "SELL", 0.7,
                                   f"StochRSI overbought ({k_val:.0f}) — correction risk")
        else:
            return IndicatorResult("StochRSI", round(k_val, 1), "NEUTRAL", 0.4,
                                   f"StochRSI neutral ({k_val:.0f})")

    # ── OBV ───────────────────────────────────────────────────────────────

    @staticmethod
    def obv(df: pd.DataFrame) -> IndicatorResult:
        df = df.copy()
        df.ta.obv(append=True)
        if "OBV" not in df:
            return IndicatorResult("OBV", None, "NEUTRAL", 0.5, "Insufficient data")

        obv_series = df["OBV"]
        obv_ema = obv_series.ewm(span=20).mean()
        obv_now = obv_series.iloc[-1]
        obv_ema_now = obv_ema.iloc[-1]
        ltp = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2] if len(df) > 1 else ltp

        price_up = ltp > prev_close
        obv_up = obv_now > obv_ema_now

        if price_up and obv_up:
            return IndicatorResult("OBV", round(obv_now, 0), "BUY", 0.8,
                                   "OBV rising with price — volume confirms trend")
        elif not price_up and not obv_up:
            return IndicatorResult("OBV", round(obv_now, 0), "SELL", 0.8,
                                   "OBV falling with price — volume confirms downtrend")
        elif price_up and not obv_up:
            return IndicatorResult("OBV", round(obv_now, 0), "SELL", 0.6,
                                   "Price up but OBV diverging — weak rally, watch out")
        else:
            return IndicatorResult("OBV", round(obv_now, 0), "BUY", 0.6,
                                   "OBV rising despite price fall — hidden accumulation")

    # ── CCI ───────────────────────────────────────────────────────────────

    @staticmethod
    def cci(df: pd.DataFrame, period: int = 20) -> IndicatorResult:
        df = df.copy()
        df.ta.cci(length=period, append=True)
        col = f"CCI_{period}_0.015"
        if col not in df:
            return IndicatorResult("CCI", None, "NEUTRAL", 0.5, "Insufficient data")

        val = df[col].iloc[-1]
        if val > 100:
            return IndicatorResult("CCI", round(val, 1), "BUY", 0.75,
                                   f"CCI {val:.0f} — strong bullish momentum")
        elif val < -100:
            return IndicatorResult("CCI", round(val, 1), "SELL", 0.75,
                                   f"CCI {val:.0f} — strong bearish momentum")
        else:
            return IndicatorResult("CCI", round(val, 1), "NEUTRAL", 0.4,
                                   f"CCI {val:.0f} — neutral zone")

    # ── MFI (Money Flow Index) ─────────────────────────────────────────────

    @staticmethod
    def mfi(df: pd.DataFrame, period: int = 14) -> IndicatorResult:
        df = df.copy()
        df.ta.mfi(length=period, append=True)
        col = f"MFI_{period}"
        if col not in df:
            return IndicatorResult("MFI", None, "NEUTRAL", 0.5, "Insufficient data")

        val = df[col].iloc[-1]
        if val < 20:
            return IndicatorResult("MFI", round(val, 1), "BUY", 0.9,
                                   f"MFI {val:.0f} — money flow oversold. Smart money buying?")
        elif val > 80:
            return IndicatorResult("MFI", round(val, 1), "SELL", 0.9,
                                   f"MFI {val:.0f} — money flow overbought. Distribution?")
        else:
            return IndicatorResult("MFI", round(val, 1), "NEUTRAL", 0.4,
                                   f"MFI {val:.0f} — neutral money flow")

    # ── Ichimoku ──────────────────────────────────────────────────────────

    @staticmethod
    def ichimoku(df: pd.DataFrame) -> IndicatorResult:
        df = df.copy()
        ichi = df.ta.ichimoku(append=False)
        if ichi is None or len(ichi) < 2:
            return IndicatorResult("Ichimoku", None, "NEUTRAL", 0.5, "Insufficient data")

        ichi_df = ichi[0]  # first result DataFrame
        ltp = df["close"].iloc[-1]

        tenkan = ichi_df.get("ITS_9", ichi_df.get("ISA_9"))
        kijun = ichi_df.get("IKS_26", ichi_df.get("ISB_26"))
        span_a = ichi_df.get("ISA_9")
        span_b = ichi_df.get("ISB_26")

        if tenkan is None or kijun is None:
            return IndicatorResult("Ichimoku", None, "NEUTRAL", 0.5, "Insufficient data")

        tenkan_val = tenkan.iloc[-1] if hasattr(tenkan, "iloc") else tenkan
        kijun_val = kijun.iloc[-1] if hasattr(kijun, "iloc") else kijun
        cloud_top = max(span_a.iloc[-1] if span_a is not None else 0,
                        span_b.iloc[-1] if span_b is not None else 0)
        cloud_bot = min(span_a.iloc[-1] if span_a is not None else 0,
                        span_b.iloc[-1] if span_b is not None else 0)

        above_cloud = ltp > cloud_top
        below_cloud = ltp < cloud_bot
        tk_cross = tenkan_val > kijun_val

        if above_cloud and tk_cross:
            return IndicatorResult("Ichimoku", f"TK:{tenkan_val:.2f}", "BUY", 0.9,
                                   "Above cloud + TK cross — very bullish Ichimoku")
        elif below_cloud and not tk_cross:
            return IndicatorResult("Ichimoku", f"TK:{tenkan_val:.2f}", "SELL", 0.9,
                                   "Below cloud + bearish TK — very bearish")
        elif above_cloud:
            return IndicatorResult("Ichimoku", f"TK:{tenkan_val:.2f}", "BUY", 0.65,
                                   "Price above cloud — bullish bias")
        elif below_cloud:
            return IndicatorResult("Ichimoku", f"TK:{tenkan_val:.2f}", "SELL", 0.65,
                                   "Price below cloud — bearish bias")
        else:
            return IndicatorResult("Ichimoku", f"TK:{tenkan_val:.2f}", "NEUTRAL", 0.3,
                                   "Price inside cloud — indecision zone")

    # ── Pivot Points ──────────────────────────────────────────────────────

    @staticmethod
    def pivot_points(prev_high: float, prev_low: float, prev_close: float) -> dict:
        """Classic pivot points from previous day's H/L/C."""
        pp = (prev_high + prev_low + prev_close) / 3
        r1 = 2 * pp - prev_low
        r2 = pp + (prev_high - prev_low)
        r3 = prev_high + 2 * (pp - prev_low)
        s1 = 2 * pp - prev_high
        s2 = pp - (prev_high - prev_low)
        s3 = prev_low - 2 * (prev_high - pp)
        return {"PP": round(pp, 2), "R1": round(r1, 2), "R2": round(r2, 2), "R3": round(r3, 2),
                "S1": round(s1, 2), "S2": round(s2, 2), "S3": round(s3, 2)}

    # ── CPR (Central Pivot Range) ─────────────────────────────────────────

    @staticmethod
    def cpr(prev_high: float, prev_low: float, prev_close: float) -> dict:
        """CPR gives the day's expected trading range and bias."""
        pivot = (prev_high + prev_low + prev_close) / 3
        bc = (prev_high + prev_low) / 2          # Bottom Central
        tc = (pivot - bc) + pivot                 # Top Central
        width = abs(tc - bc)
        is_narrow = width < (prev_close * 0.003)  # < 0.3% = narrow CPR = trending day

        return {
            "pivot": round(pivot, 2),
            "tc": round(tc, 2),
            "bc": round(bc, 2),
            "width": round(width, 2),
            "is_narrow": is_narrow,
            "bias": "TRENDING" if is_narrow else "SIDEWAYS",
        }

    # ── Master Compute ────────────────────────────────────────────────────

    def compute_all(
        self,
        df: pd.DataFrame,
        timeframe: str,
        prev_high: float = None,
        prev_low: float = None,
        prev_close: float = None,
        is_intraday: bool = True,
    ) -> MultiTFIndicators:
        """
        Compute all 19 indicators on a given OHLCV DataFrame.
        Returns a MultiTFIndicators dataclass.
        """
        result = MultiTFIndicators(timeframe=timeframe)
        if df is None or len(df) < 20:
            logger.warning(f"Insufficient data for {timeframe} indicators: {len(df) if df is not None else 0} bars")
            return result

        try:
            result.rsi = self.rsi(df)
            result.macd = self.macd(df)
            result.ema_20 = self.ema(df, 20)
            result.ema_50 = self.ema(df, 50)
            result.ema_200 = self.ema(df, 200) if len(df) >= 200 else None
            result.bollinger = self.bollinger(df)
            result.atr = self.atr(df)
            result.adx = self.adx(df)
            result.supertrend = self.supertrend(df)
            result.stoch_rsi = self.stoch_rsi(df)
            result.obv = self.obv(df)
            result.cci = self.cci(df)
            result.mfi = self.mfi(df)
            result.ichimoku = self.ichimoku(df)

            if is_intraday:
                result.vwap = self.vwap(df)

            if prev_high and prev_low and prev_close:
                result.pivot_points = self.pivot_points(prev_high, prev_low, prev_close)

            # Tally signals
            all_indicators = [
                result.rsi, result.macd, result.ema_20, result.ema_50,
                result.bollinger, result.adx, result.supertrend, result.stoch_rsi,
                result.obv, result.cci, result.mfi, result.ichimoku,
            ]
            if result.vwap:
                all_indicators.append(result.vwap)

            for ind in all_indicators:
                if ind and ind.signal == "BUY":
                    result.buy_count += 1
                elif ind and ind.signal == "SELL":
                    result.sell_count += 1
                else:
                    result.neutral_count += 1

            total = result.buy_count + result.sell_count + result.neutral_count
            if total > 0:
                result.bull_score = (result.buy_count / total) * 100

            if result.buy_count > result.sell_count:
                result.overall_signal = "BUY"
            elif result.sell_count > result.buy_count:
                result.overall_signal = "SELL"
            else:
                result.overall_signal = "NEUTRAL"

        except Exception as e:
            logger.error(f"Indicator computation error for {timeframe}: {e}")

        return result


indicator_engine = IndicatorEngine()

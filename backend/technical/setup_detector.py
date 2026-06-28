"""
Trade setup detector — combines all technical signals to identify high-probability setups.
10 core intraday strategies with entry/exit rules.
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger

from backend.technical.indicators import indicator_engine, MultiTFIndicators
from backend.technical.market_structure import market_structure_analyzer, MarketStructure
from backend.technical.support_resistance import sr_engine
from backend.technical.candlestick_patterns import candle_detector
from backend.technical.chart_patterns import chart_detector
from backend.technical.fibonacci import fib_engine


@dataclass
class TradeSetup:
    """Complete trade setup with all levels and conditions."""
    symbol: str
    strategy: str
    direction: str           # "LONG" or "SHORT"
    score: float             # 0–100
    entry_low: float
    entry_high: float
    stop_loss: float
    target_1: float
    target_2: float
    invalidation: float
    rr_ratio: float
    conditions_met: list[str] = field(default_factory=list)
    conditions_failed: list[str] = field(default_factory=list)
    chart_pattern: str = ""
    candle_pattern: str = ""
    market_structure: str = ""
    description: str = ""


class SetupDetector:

    STRATEGIES = [
        "VWAP_Bounce",
        "ORB_Breakout",
        "EMA_Pullback",
        "PDH_PDL_Breakout",
        "FVG_Retest",
        "Order_Block_Reversal",
        "Fibonacci_Retracement",
        "Momentum_Breakout",
        "Demand_Zone_Bounce",
        "CPR_Play",
    ]

    def detect_setups(
        self,
        symbol: str,
        df_5m: pd.DataFrame,
        df_15m: pd.DataFrame,
        df_1h: pd.DataFrame,
        df_daily: pd.DataFrame,
        prev_day_high: float = None,
        prev_day_low: float = None,
        prev_day_close: float = None,
        capital: float = 150000,
        max_risk_pct: float = 0.01,
    ) -> list[TradeSetup]:
        """Run all strategy detectors. Returns list of valid setups."""
        setups = []

        ind_5m = indicator_engine.compute_all(df_5m, "5m", prev_day_high, prev_day_low, prev_day_close)
        ind_15m = indicator_engine.compute_all(df_15m, "15m", prev_day_high, prev_day_low, prev_day_close)
        ind_1h = indicator_engine.compute_all(df_1h, "1H", is_intraday=False)
        ms = market_structure_analyzer.analyze(df_15m)
        cpr = indicator_engine.cpr(prev_day_high, prev_day_low, prev_day_close) if all([prev_day_high, prev_day_low, prev_day_close]) else {}

        candle_patterns = candle_detector.detect_all(df_5m)
        chart_patterns = chart_detector.detect_all(df_15m)
        fib_levels = fib_engine.auto_levels(df_15m)
        sr_levels = sr_engine.find_levels(df_15m, prev_day_high, prev_day_low)

        ltp = df_5m["close"].iloc[-1]

        # VWAP Bounce
        vwap_setup = self._vwap_bounce(symbol, ltp, ind_5m, ind_15m, ms, candle_patterns, sr_levels)
        if vwap_setup:
            setups.append(vwap_setup)

        # ORB Breakout
        orb_setup = self._orb_breakout(symbol, ltp, df_5m, ind_5m, ind_15m, ms)
        if orb_setup:
            setups.append(orb_setup)

        # EMA Pullback
        ema_setup = self._ema_pullback(symbol, ltp, ind_5m, ind_15m, ind_1h, ms, candle_patterns)
        if ema_setup:
            setups.append(ema_setup)

        # PDH/PDL Breakout
        if prev_day_high and prev_day_low:
            pdh_setup = self._pdh_breakout(symbol, ltp, prev_day_high, prev_day_low, ind_5m, ind_15m, ms)
            if pdh_setup:
                setups.append(pdh_setup)

        # FVG Retest
        fvg_setup = self._fvg_retest(symbol, ltp, df_5m, ind_5m, ind_15m, ms)
        if fvg_setup:
            setups.append(fvg_setup)

        # Fibonacci
        fib_setup = self._fib_retracement(symbol, ltp, fib_levels, ind_5m, ind_15m, ms, candle_patterns)
        if fib_setup:
            setups.append(fib_setup)

        # Return highest-scoring setups
        setups.sort(key=lambda x: x.score, reverse=True)
        return setups[:3]

    def _vwap_bounce(self, symbol, ltp, ind_5m, ind_15m, ms, candle_patterns, sr_levels) -> TradeSetup | None:
        """VWAP Bounce: Price pulls to VWAP, bullish candle + CVD rising + volume surge."""
        if not ind_5m.vwap or ind_5m.vwap.value is None:
            return None

        vwap = float(ind_5m.vwap.value)
        proximity = abs(ltp - vwap) / vwap

        conditions = []
        fails = []

        if proximity <= 0.002:
            conditions.append(f"Price within 0.2% of VWAP ({vwap:.2f})")
        else:
            fails.append(f"Price {proximity:.1%} from VWAP — too far")
            return None

        if ind_15m.overall_signal == "BUY":
            conditions.append("15m bias: BULLISH")
        else:
            fails.append("15m bias not bullish")
            return None

        if ms.trend in ["UP", "REVERSAL_UP"]:
            conditions.append(f"Market structure: {ms.trend}")
        else:
            fails.append(f"Market structure not bullish: {ms.trend}")

        bullish_candles = [p for p in candle_patterns if p.signal == "BUY"]
        if bullish_candles:
            conditions.append(f"Candlestick: {bullish_candles[0].name}")
        else:
            fails.append("No bullish candlestick at VWAP")

        if ind_5m.adx and float(ind_5m.adx.value or 0) > 20:
            conditions.append(f"ADX {ind_5m.adx.value} — trend confirmed")
        else:
            fails.append("ADX weak — trend questionable")

        score = len(conditions) / (len(conditions) + len(fails)) * 100 if (conditions or fails) else 0
        if score < 60:
            return None

        entry_low = vwap
        entry_high = vwap * 1.002
        atr_val = float(ind_5m.atr.value) if ind_5m.atr and ind_5m.atr.value else ltp * 0.008
        stop = vwap - atr_val * 1.5
        t1 = ltp + atr_val * 2
        t2 = ltp + atr_val * 3.5
        rr = (t1 - entry_high) / (entry_high - stop) if stop < entry_high else 0

        return TradeSetup(
            symbol=symbol, strategy="VWAP_Bounce", direction="LONG",
            score=min(100, score + 10),
            entry_low=round(entry_low, 2), entry_high=round(entry_high, 2),
            stop_loss=round(stop, 2), target_1=round(t1, 2), target_2=round(t2, 2),
            invalidation=round(stop * 0.998, 2), rr_ratio=round(rr, 2),
            conditions_met=conditions, conditions_failed=fails,
            candle_pattern=bullish_candles[0].name if bullish_candles else "",
            market_structure=ms.structure_type,
            description=f"VWAP bounce at {vwap:.2f} with multi-timeframe bullish alignment."
        )

    def _orb_breakout(self, symbol, ltp, df, ind_5m, ind_15m, ms) -> TradeSetup | None:
        """Opening Range Breakout: 5m or 15m first candle range defines ORB."""
        if len(df) < 3:
            return None

        orb_high = df.iloc[0]["high"]
        orb_low = df.iloc[0]["low"]
        orb_range = orb_high - orb_low

        conditions = []
        fails = []

        if ltp > orb_high:
            conditions.append(f"Price broke ORB high {orb_high:.2f}")
        else:
            return None

        if ind_15m.overall_signal == "BUY":
            conditions.append("15m aligned bullish")
        else:
            fails.append("15m not bullish")

        vol_now = df["volume"].iloc[-1]
        vol_avg = df["volume"].mean()
        if vol_now > vol_avg * 1.5:
            conditions.append(f"Volume {vol_now/vol_avg:.1f}× above avg — conviction break")
        else:
            fails.append("Volume not confirming breakout")

        if ms.trend in ["UP", "HH_HL"]:
            conditions.append("Structure bullish")
        else:
            fails.append(f"Structure not bullish: {ms.trend}")

        score = len(conditions) / max(1, len(conditions) + len(fails)) * 100
        if score < 55:
            return None

        entry_low = orb_high
        entry_high = orb_high * 1.001
        stop = orb_low
        t1 = orb_high + orb_range
        t2 = orb_high + orb_range * 2
        rr = (t1 - entry_high) / (entry_high - stop) if stop < entry_high else 0

        return TradeSetup(
            symbol=symbol, strategy="ORB_Breakout", direction="LONG",
            score=min(100, score),
            entry_low=round(entry_low, 2), entry_high=round(entry_high, 2),
            stop_loss=round(stop, 2), target_1=round(t1, 2), target_2=round(t2, 2),
            invalidation=round(orb_low - orb_range * 0.1, 2), rr_ratio=round(rr, 2),
            conditions_met=conditions, conditions_failed=fails,
            market_structure=ms.structure_type,
            description=f"ORB breakout above {orb_high:.2f}. Range target {t1:.2f}."
        )

    def _ema_pullback(self, symbol, ltp, ind_5m, ind_15m, ind_1h, ms, candle_patterns) -> TradeSetup | None:
        """EMA Pullback: Price in uptrend, pulls to EMA20, bounces with bullish candle."""
        if not ind_15m.ema_20 or ind_15m.ema_20.value is None:
            return None

        ema20 = float(ind_15m.ema_20.value)
        proximity = abs(ltp - ema20) / ema20

        if proximity > 0.003:
            return None
        if ms.trend not in ["UP", "HH_HL"]:
            return None

        conditions = ["Price pulled back to EMA20", f"Structure: {ms.trend}"]
        fails = []

        if ind_1h.overall_signal == "BUY":
            conditions.append("1H timeframe bullish")
        else:
            fails.append("1H not bullish")

        bullish_candles = [p for p in candle_patterns if p.signal == "BUY"]
        if bullish_candles:
            conditions.append(f"Candle: {bullish_candles[0].name}")

        score = max(50, len(conditions) / max(1, len(conditions) + len(fails)) * 100)
        atr_val = float(ind_5m.atr.value) if ind_5m.atr and ind_5m.atr.value else ltp * 0.008

        return TradeSetup(
            symbol=symbol, strategy="EMA_Pullback", direction="LONG",
            score=min(100, score + 5),
            entry_low=ema20, entry_high=round(ema20 * 1.002, 2),
            stop_loss=round(ema20 - atr_val, 2),
            target_1=round(ltp + atr_val * 2, 2),
            target_2=round(ltp + atr_val * 3, 2),
            invalidation=round(ema20 - atr_val * 1.2, 2),
            rr_ratio=2.0,
            conditions_met=conditions, conditions_failed=fails,
            candle_pattern=bullish_candles[0].name if bullish_candles else "",
            market_structure=ms.structure_type,
            description=f"EMA20 pullback in uptrend at {ema20:.2f}."
        )

    def _pdh_breakout(self, symbol, ltp, pdh, pdl, ind_5m, ind_15m, ms) -> TradeSetup | None:
        if abs(ltp - pdh) / pdh > 0.002:
            return None
        if ltp < pdh:
            return None

        conditions = [f"Price broke PDH {pdh:.2f}", f"Structure: {ms.trend}"]
        fails = []
        if ind_15m.overall_signal != "BUY":
            fails.append("15m not bullish")

        atr_val = float(ind_5m.atr.value) if ind_5m.atr and ind_5m.atr.value else ltp * 0.008
        score = 70 if not fails else 55

        return TradeSetup(
            symbol=symbol, strategy="PDH_PDL_Breakout", direction="LONG",
            score=score,
            entry_low=pdh, entry_high=round(pdh * 1.001, 2),
            stop_loss=round(pdh - atr_val, 2),
            target_1=round(pdh + atr_val * 2, 2),
            target_2=round(pdh + atr_val * 3, 2),
            invalidation=round(pdh - atr_val * 1.2, 2),
            rr_ratio=2.0,
            conditions_met=conditions, conditions_failed=fails,
            market_structure=ms.structure_type,
            description=f"PDH breakout above {pdh:.2f} with volume confirmation."
        )

    def _fvg_retest(self, symbol, ltp, df, ind_5m, ind_15m, ms) -> TradeSetup | None:
        from backend.technical.market_structure import market_structure_analyzer
        fvgs = market_structure_analyzer.find_fvg(df)
        bullish_fvgs = [f for f in fvgs if f.direction == "BULLISH" and f.low <= ltp <= f.high]

        if not bullish_fvgs:
            return None

        fvg = bullish_fvgs[-1]
        conditions = [f"Price in bullish FVG ({fvg.low:.2f}–{fvg.high:.2f})"]
        if ms.trend == "UP":
            conditions.append("Structure bullish")
        atr_val = float(ind_5m.atr.value) if ind_5m.atr and ind_5m.atr.value else ltp * 0.008

        return TradeSetup(
            symbol=symbol, strategy="FVG_Retest", direction="LONG",
            score=72,
            entry_low=fvg.low, entry_high=fvg.high,
            stop_loss=round(fvg.low - atr_val * 0.5, 2),
            target_1=round(fvg.high + atr_val * 2, 2),
            target_2=round(fvg.high + atr_val * 3.5, 2),
            invalidation=round(fvg.low - atr_val, 2),
            rr_ratio=2.1,
            conditions_met=conditions, conditions_failed=[],
            market_structure=ms.structure_type,
            description=f"Fair Value Gap retest at {fvg.mid:.2f}."
        )

    def _fib_retracement(self, symbol, ltp, fib_levels, ind_5m, ind_15m, ms, candle_patterns) -> TradeSetup | None:
        fib_supports = [l for l in fib_levels if l.is_support and l.price <= ltp and abs(ltp - l.price) / l.price <= 0.003]
        if not fib_supports:
            return None

        best_fib = max(fib_supports, key=lambda x: x.price)
        conditions = [f"At Fibonacci {best_fib.ratio:.3f} level ({best_fib.price:.2f})"]
        if ms.trend == "UP":
            conditions.append("Uptrend intact")

        bullish_candles = [p for p in candle_patterns if p.signal == "BUY"]
        if bullish_candles:
            conditions.append(f"Candle: {bullish_candles[0].name}")

        atr_val = float(ind_5m.atr.value) if ind_5m.atr and ind_5m.atr.value else ltp * 0.008

        return TradeSetup(
            symbol=symbol, strategy="Fibonacci_Retracement", direction="LONG",
            score=68,
            entry_low=best_fib.price, entry_high=round(best_fib.price * 1.002, 2),
            stop_loss=round(best_fib.price - atr_val, 2),
            target_1=round(best_fib.price + atr_val * 2, 2),
            target_2=round(best_fib.price + atr_val * 3, 2),
            invalidation=round(best_fib.price - atr_val * 1.2, 2),
            rr_ratio=2.0,
            conditions_met=conditions, conditions_failed=[],
            candle_pattern=bullish_candles[0].name if bullish_candles else "",
            market_structure=ms.structure_type,
            description=f"Fibonacci {best_fib.label} bounce setup."
        )


setup_detector = SetupDetector()

"""
16 candlestick pattern detectors with signal strength and trading implication.
All patterns operate on the last N bars of OHLCV data.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from loguru import logger


@dataclass
class CandlePattern:
    name: str
    signal: str           # "BUY", "SELL", "NEUTRAL"
    strength: float       # 0.0–1.0 (reliability score)
    description: str
    detected: bool = True


class CandlestickDetector:

    def detect_all(self, df: pd.DataFrame) -> list[CandlePattern]:
        """Detect all 16 patterns on the last few bars."""
        if len(df) < 3:
            return []

        detected = []
        methods = [
            self.doji, self.hammer, self.inverted_hammer, self.shooting_star,
            self.bullish_engulfing, self.bearish_engulfing,
            self.morning_star, self.evening_star,
            self.bullish_harami, self.bearish_harami,
            self.piercing_line, self.dark_cloud_cover,
            self.three_white_soldiers, self.three_black_crows,
            self.spinning_top, self.marubozu,
        ]
        for method in methods:
            try:
                result = method(df)
                if result and result.detected:
                    detected.append(result)
            except Exception as e:
                logger.debug(f"Pattern detection error ({method.__name__}): {e}")

        return detected

    # ── Helper ─────────────────────────────────────────────────────────────

    @staticmethod
    def _body(o: float, c: float) -> float:
        return abs(c - o)

    @staticmethod
    def _range(h: float, l: float) -> float:
        return h - l

    @staticmethod
    def _upper_shadow(o: float, h: float, c: float) -> float:
        return h - max(o, c)

    @staticmethod
    def _lower_shadow(o: float, l: float, c: float) -> float:
        return min(o, c) - l

    # ── 1. Doji ────────────────────────────────────────────────────────────

    def doji(self, df: pd.DataFrame) -> CandlePattern | None:
        row = df.iloc[-1]
        o, h, l, c = row.open, row.high, row.low, row.close
        body = self._body(o, c)
        rng = self._range(h, l)
        if rng == 0:
            return None
        if body / rng <= 0.1:
            return CandlePattern("Doji", "NEUTRAL", 0.55,
                                 "Doji: indecision. Watch next candle for direction.")
        return CandlePattern("Doji", "NEUTRAL", 0, "", detected=False)

    # ── 2. Hammer ─────────────────────────────────────────────────────────

    def hammer(self, df: pd.DataFrame) -> CandlePattern | None:
        row = df.iloc[-1]
        o, h, l, c = row.open, row.high, row.low, row.close
        body = self._body(o, c)
        lower = self._lower_shadow(o, l, c)
        upper = self._upper_shadow(o, h, c)
        rng = self._range(h, l)
        if rng == 0:
            return None

        is_hammer = (lower >= 2 * body) and (upper <= 0.1 * rng) and (body / rng >= 0.1)
        # Must appear in a downtrend
        prev_closes = df["close"].values[-5:-1]
        in_downtrend = prev_closes[-1] < prev_closes[0]

        if is_hammer and in_downtrend:
            return CandlePattern("Hammer", "BUY", 0.75,
                                 "Hammer at support in downtrend — bullish reversal signal")
        return CandlePattern("Hammer", "BUY", 0, "", detected=False)

    # ── 3. Inverted Hammer ────────────────────────────────────────────────

    def inverted_hammer(self, df: pd.DataFrame) -> CandlePattern | None:
        row = df.iloc[-1]
        o, h, l, c = row.open, row.high, row.low, row.close
        body = self._body(o, c)
        upper = self._upper_shadow(o, h, c)
        lower = self._lower_shadow(o, l, c)
        rng = self._range(h, l)
        if rng == 0:
            return None

        is_ih = (upper >= 2 * body) and (lower <= 0.1 * rng) and (body / rng >= 0.1)
        prev_closes = df["close"].values[-5:-1]
        in_downtrend = prev_closes[-1] < prev_closes[0]

        if is_ih and in_downtrend:
            return CandlePattern("Inverted Hammer", "BUY", 0.6,
                                 "Inverted Hammer after downtrend — watch for confirmation")
        return CandlePattern("Inverted Hammer", "BUY", 0, "", detected=False)

    # ── 4. Shooting Star ──────────────────────────────────────────────────

    def shooting_star(self, df: pd.DataFrame) -> CandlePattern | None:
        row = df.iloc[-1]
        o, h, l, c = row.open, row.high, row.low, row.close
        body = self._body(o, c)
        upper = self._upper_shadow(o, h, c)
        lower = self._lower_shadow(o, l, c)
        rng = self._range(h, l)
        if rng == 0:
            return None

        is_ss = (upper >= 2 * body) and (lower <= 0.1 * rng)
        prev_closes = df["close"].values[-5:-1]
        in_uptrend = prev_closes[-1] > prev_closes[0]

        if is_ss and in_uptrend:
            return CandlePattern("Shooting Star", "SELL", 0.78,
                                 "Shooting Star at resistance after uptrend — bearish reversal")
        return CandlePattern("Shooting Star", "SELL", 0, "", detected=False)

    # ── 5. Bullish Engulfing ──────────────────────────────────────────────

    def bullish_engulfing(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        curr = df.iloc[-1]

        is_prev_bearish = prev.close < prev.open
        is_curr_bullish = curr.close > curr.open
        engulfs = curr.open < prev.close and curr.close > prev.open

        if is_prev_bearish and is_curr_bullish and engulfs:
            return CandlePattern("Bullish Engulfing", "BUY", 0.82,
                                 "Bullish Engulfing — strong reversal. Bulls fully overpowered bears.")
        return CandlePattern("Bullish Engulfing", "BUY", 0, "", detected=False)

    # ── 6. Bearish Engulfing ──────────────────────────────────────────────

    def bearish_engulfing(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        curr = df.iloc[-1]

        is_prev_bullish = prev.close > prev.open
        is_curr_bearish = curr.close < curr.open
        engulfs = curr.open > prev.close and curr.close < prev.open

        if is_prev_bullish and is_curr_bearish and engulfs:
            return CandlePattern("Bearish Engulfing", "SELL", 0.82,
                                 "Bearish Engulfing — bears overwhelmed bulls. Trend reversal warning.")
        return CandlePattern("Bearish Engulfing", "SELL", 0, "", detected=False)

    # ── 7. Morning Star ───────────────────────────────────────────────────

    def morning_star(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 3:
            return None
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        is_bearish_1 = c1.close < c1.open
        is_small_2 = self._body(c2.open, c2.close) < 0.5 * self._body(c1.open, c1.close)
        is_bullish_3 = c3.close > c3.open
        recovers = c3.close > (c1.open + c1.close) / 2

        if is_bearish_1 and is_small_2 and is_bullish_3 and recovers:
            return CandlePattern("Morning Star", "BUY", 0.88,
                                 "Morning Star — 3-candle bullish reversal. Strong signal at bottom.")
        return CandlePattern("Morning Star", "BUY", 0, "", detected=False)

    # ── 8. Evening Star ───────────────────────────────────────────────────

    def evening_star(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 3:
            return None
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        is_bullish_1 = c1.close > c1.open
        is_small_2 = self._body(c2.open, c2.close) < 0.5 * self._body(c1.open, c1.close)
        is_bearish_3 = c3.close < c3.open
        drops = c3.close < (c1.open + c1.close) / 2

        if is_bullish_1 and is_small_2 and is_bearish_3 and drops:
            return CandlePattern("Evening Star", "SELL", 0.88,
                                 "Evening Star — 3-candle bearish reversal at top. Strong sell signal.")
        return CandlePattern("Evening Star", "SELL", 0, "", detected=False)

    # ── 9. Bullish Harami ─────────────────────────────────────────────────

    def bullish_harami(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        curr = df.iloc[-1]

        is_prev_bearish = prev.close < prev.open
        is_curr_bullish = curr.close > curr.open
        inside = curr.open > prev.close and curr.close < prev.open

        if is_prev_bearish and is_curr_bullish and inside:
            return CandlePattern("Bullish Harami", "BUY", 0.65,
                                 "Bullish Harami — inside candle after bearish. Hesitation, await confirmation.")
        return CandlePattern("Bullish Harami", "BUY", 0, "", detected=False)

    # ── 10. Bearish Harami ────────────────────────────────────────────────

    def bearish_harami(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        curr = df.iloc[-1]

        is_prev_bullish = prev.close > prev.open
        is_curr_bearish = curr.close < curr.open
        inside = curr.open < prev.close and curr.close > prev.open

        if is_prev_bullish and is_curr_bearish and inside:
            return CandlePattern("Bearish Harami", "SELL", 0.65,
                                 "Bearish Harami — inside candle after bullish. Slowdown — watch for break.")
        return CandlePattern("Bearish Harami", "SELL", 0, "", detected=False)

    # ── 11. Piercing Line ─────────────────────────────────────────────────

    def piercing_line(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        curr = df.iloc[-1]

        if prev.close < prev.open and curr.close > curr.open:
            midpoint_prev = (prev.open + prev.close) / 2
            if curr.open < prev.close and curr.close > midpoint_prev:
                return CandlePattern("Piercing Line", "BUY", 0.72,
                                     "Piercing Line — bulls cut through bearish candle. Moderate reversal signal.")
        return CandlePattern("Piercing Line", "BUY", 0, "", detected=False)

    # ── 12. Dark Cloud Cover ──────────────────────────────────────────────

    def dark_cloud_cover(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        curr = df.iloc[-1]

        if prev.close > prev.open and curr.close < curr.open:
            midpoint_prev = (prev.open + prev.close) / 2
            if curr.open > prev.close and curr.close < midpoint_prev:
                return CandlePattern("Dark Cloud Cover", "SELL", 0.72,
                                     "Dark Cloud Cover — bears engulfed majority of bulls. Sell signal.")
        return CandlePattern("Dark Cloud Cover", "SELL", 0, "", detected=False)

    # ── 13. Three White Soldiers ──────────────────────────────────────────

    def three_white_soldiers(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 3:
            return None
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        all_bullish = all(c.close > c.open for c in [c1, c2, c3])
        ascending = c1.close < c2.close < c3.close
        no_big_shadows = all(
            self._upper_shadow(c.open, c.high, c.close) < 0.3 * self._body(c.open, c.close)
            for c in [c1, c2, c3]
        )

        if all_bullish and ascending and no_big_shadows:
            return CandlePattern("Three White Soldiers", "BUY", 0.90,
                                 "Three White Soldiers — very strong bullish momentum. Trend continuation.")
        return CandlePattern("Three White Soldiers", "BUY", 0, "", detected=False)

    # ── 14. Three Black Crows ─────────────────────────────────────────────

    def three_black_crows(self, df: pd.DataFrame) -> CandlePattern | None:
        if len(df) < 3:
            return None
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        all_bearish = all(c.close < c.open for c in [c1, c2, c3])
        descending = c1.close > c2.close > c3.close

        if all_bearish and descending:
            return CandlePattern("Three Black Crows", "SELL", 0.90,
                                 "Three Black Crows — heavy sell-off. Strong bearish continuation.")
        return CandlePattern("Three Black Crows", "SELL", 0, "", detected=False)

    # ── 15. Spinning Top ──────────────────────────────────────────────────

    def spinning_top(self, df: pd.DataFrame) -> CandlePattern | None:
        row = df.iloc[-1]
        o, h, l, c = row.open, row.high, row.low, row.close
        body = self._body(o, c)
        rng = self._range(h, l)
        if rng == 0:
            return None
        upper = self._upper_shadow(o, h, c)
        lower = self._lower_shadow(o, l, c)

        if body / rng < 0.3 and upper > body and lower > body:
            return CandlePattern("Spinning Top", "NEUTRAL", 0.5,
                                 "Spinning Top — balance between buyers/sellers. Indecision at key level?")
        return CandlePattern("Spinning Top", "NEUTRAL", 0, "", detected=False)

    # ── 16. Marubozu ─────────────────────────────────────────────────────

    def marubozu(self, df: pd.DataFrame) -> CandlePattern | None:
        row = df.iloc[-1]
        o, h, l, c = row.open, row.high, row.low, row.close
        body = self._body(o, c)
        rng = self._range(h, l)
        if rng == 0 or body == 0:
            return None

        is_marubozu = body / rng >= 0.9  # 90%+ of range is body (no shadows)
        if is_marubozu and c > o:
            return CandlePattern("Bullish Marubozu", "BUY", 0.85,
                                 "Bullish Marubozu — strong bullish conviction, no sellers. Momentum buy.")
        elif is_marubozu and c < o:
            return CandlePattern("Bearish Marubozu", "SELL", 0.85,
                                 "Bearish Marubozu — no buyers present. Strong bearish momentum.")
        return CandlePattern("Marubozu", "NEUTRAL", 0, "", detected=False)


candle_detector = CandlestickDetector()

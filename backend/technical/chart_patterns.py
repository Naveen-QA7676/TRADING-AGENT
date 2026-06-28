"""
Chart pattern detection: 16 major patterns.
Each returns the pattern name, signal, target, and stop loss suggestion.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from backend.technical.market_structure import market_structure_analyzer


@dataclass
class ChartPattern:
    name: str
    signal: str           # "BUY", "SELL", "NEUTRAL"
    strength: float       # 0–1
    price_target: float | None
    stop_suggestion: float | None
    description: str
    detected: bool = True


class ChartPatternDetector:

    def detect_all(self, df: pd.DataFrame) -> list[ChartPattern]:
        results = []
        methods = [
            self.double_bottom, self.double_top,
            self.head_and_shoulders, self.inverse_head_and_shoulders,
            self.ascending_triangle, self.descending_triangle, self.symmetrical_triangle,
            self.bull_flag, self.bear_flag,
            self.cup_and_handle,
            self.rounding_bottom,
            self.rising_wedge, self.falling_wedge,
            self.channel_up, self.channel_down,
            self.orb,
        ]
        for method in methods:
            try:
                result = method(df)
                if result and result.detected:
                    results.append(result)
            except Exception:
                pass
        return results

    # ── Double Bottom ──────────────────────────────────────────────────────

    def double_bottom(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 20:
            return None
        lows = df["low"].values
        swings = market_structure_analyzer.find_swing_points(df, lookback=3)
        swing_lows = [s for s in swings if s.swing_type == "LOW"]

        if len(swing_lows) < 2:
            return None

        l1, l2 = swing_lows[-2], swing_lows[-1]
        if abs(l1.price - l2.price) / l1.price > 0.02:  # within 2%
            return None

        neckline = df["high"].values[l1.index:l2.index].max()
        ltp = df["close"].iloc[-1]

        if ltp >= neckline:
            target = neckline + (neckline - l2.price)
            return ChartPattern("Double Bottom", "BUY", 0.82, target, l2.price * 0.995,
                                f"Double Bottom confirmed at {l2.price:.2f}. Target: {target:.2f}")
        return ChartPattern("Double Bottom", "BUY", 0, None, None, "", detected=False)

    # ── Double Top ─────────────────────────────────────────────────────────

    def double_top(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 20:
            return None
        swings = market_structure_analyzer.find_swing_points(df, lookback=3)
        swing_highs = [s for s in swings if s.swing_type == "HIGH"]

        if len(swing_highs) < 2:
            return None

        h1, h2 = swing_highs[-2], swing_highs[-1]
        if abs(h1.price - h2.price) / h1.price > 0.02:
            return None

        neckline = df["low"].values[h1.index:h2.index].min()
        ltp = df["close"].iloc[-1]

        if ltp <= neckline:
            target = neckline - (h2.price - neckline)
            return ChartPattern("Double Top", "SELL", 0.82, target, h2.price * 1.005,
                                f"Double Top breakdown below {neckline:.2f}. Target: {target:.2f}")
        return ChartPattern("Double Top", "SELL", 0, None, None, "", detected=False)

    # ── Head and Shoulders ─────────────────────────────────────────────────

    def head_and_shoulders(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 30:
            return None
        swings = market_structure_analyzer.find_swing_points(df, lookback=3)
        highs = [s for s in swings if s.swing_type == "HIGH"]

        if len(highs) < 3:
            return None

        ls, head, rs = highs[-3], highs[-2], highs[-1]
        is_hs = (head.price > ls.price) and (head.price > rs.price) and \
                (abs(ls.price - rs.price) / ls.price < 0.05)

        if is_hs:
            neckline = df["low"].values[ls.index:rs.index].mean()
            ltp = df["close"].iloc[-1]
            if ltp < neckline:
                target = neckline - (head.price - neckline)
                return ChartPattern("Head & Shoulders", "SELL", 0.88, target, rs.price,
                                    f"H&S breakdown. Neckline {neckline:.2f} breached. Target {target:.2f}")
        return ChartPattern("Head & Shoulders", "SELL", 0, None, None, "", detected=False)

    # ── Inverse Head and Shoulders ────────────────────────────────────────

    def inverse_head_and_shoulders(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 30:
            return None
        swings = market_structure_analyzer.find_swing_points(df, lookback=3)
        lows = [s for s in swings if s.swing_type == "LOW"]

        if len(lows) < 3:
            return None

        ls, head, rs = lows[-3], lows[-2], lows[-1]
        is_ihs = (head.price < ls.price) and (head.price < rs.price) and \
                 (abs(ls.price - rs.price) / ls.price < 0.05)

        if is_ihs:
            neckline = df["high"].values[ls.index:rs.index].mean()
            ltp = df["close"].iloc[-1]
            if ltp > neckline:
                target = neckline + (neckline - head.price)
                return ChartPattern("Inverse H&S", "BUY", 0.88, target, rs.price,
                                    f"Inverse H&S breakout above {neckline:.2f}. Target {target:.2f}")
        return ChartPattern("Inverse H&S", "BUY", 0, None, None, "", detected=False)

    # ── Ascending Triangle ────────────────────────────────────────────────

    def ascending_triangle(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 15:
            return None
        last_n = df.tail(15)
        highs = last_n["high"].values
        lows = last_n["low"].values

        high_flat = (highs.max() - highs.min()) / highs.mean() < 0.01
        low_rising = np.polyfit(range(len(lows)), lows, 1)[0] > 0
        ltp = df["close"].iloc[-1]

        if high_flat and low_rising:
            resistance = highs.max()
            if ltp >= resistance:
                target = resistance + (resistance - lows.min())
                return ChartPattern("Ascending Triangle", "BUY", 0.78, target,
                                    lows.min(), f"Ascending triangle breakout. Target {target:.2f}")
        return ChartPattern("Ascending Triangle", "BUY", 0, None, None, "", detected=False)

    # ── Descending Triangle ───────────────────────────────────────────────

    def descending_triangle(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 15:
            return None
        last_n = df.tail(15)
        highs = last_n["high"].values
        lows = last_n["low"].values

        low_flat = (lows.max() - lows.min()) / lows.mean() < 0.01
        high_falling = np.polyfit(range(len(highs)), highs, 1)[0] < 0
        ltp = df["close"].iloc[-1]

        if low_flat and high_falling:
            support = lows.min()
            if ltp <= support:
                target = support - (highs.max() - support)
                return ChartPattern("Descending Triangle", "SELL", 0.78, target,
                                    highs.max(), f"Descending triangle breakdown. Target {target:.2f}")
        return ChartPattern("Descending Triangle", "SELL", 0, None, None, "", detected=False)

    # ── Symmetrical Triangle ──────────────────────────────────────────────

    def symmetrical_triangle(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 15:
            return None
        last_n = df.tail(15)
        highs = last_n["high"].values
        lows = last_n["low"].values
        high_slope = np.polyfit(range(len(highs)), highs, 1)[0]
        low_slope = np.polyfit(range(len(lows)), lows, 1)[0]

        if high_slope < 0 and low_slope > 0:
            return ChartPattern("Symmetrical Triangle", "NEUTRAL", 0.6, None, None,
                                "Symmetrical triangle — coiling. Breakout direction TBD.")
        return ChartPattern("Symmetrical Triangle", "NEUTRAL", 0, None, None, "", detected=False)

    # ── Bull Flag ─────────────────────────────────────────────────────────

    def bull_flag(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 20:
            return None
        pole = df.tail(20).head(10)
        flag = df.tail(10)

        pole_gain = (pole["close"].iloc[-1] - pole["close"].iloc[0]) / pole["close"].iloc[0]
        flag_retrace = (flag["close"].iloc[0] - flag["close"].iloc[-1]) / flag["close"].iloc[0]
        flag_slope = np.polyfit(range(len(flag)), flag["close"].values, 1)[0]

        if pole_gain > 0.03 and 0.003 < flag_retrace < 0.015 and flag_slope < 0:
            pole_size = pole["close"].iloc[-1] - pole["close"].iloc[0]
            target = df["close"].iloc[-1] + pole_size
            stop = flag["low"].min()
            return ChartPattern("Bull Flag", "BUY", 0.80, target, stop,
                                f"Bull flag ready. Pole gain {pole_gain:.1%}. Target {target:.2f}")
        return ChartPattern("Bull Flag", "BUY", 0, None, None, "", detected=False)

    # ── Bear Flag ─────────────────────────────────────────────────────────

    def bear_flag(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 20:
            return None
        pole = df.tail(20).head(10)
        flag = df.tail(10)

        pole_drop = (pole["close"].iloc[0] - pole["close"].iloc[-1]) / pole["close"].iloc[0]
        flag_retrace = (flag["close"].iloc[-1] - flag["close"].iloc[0]) / flag["close"].iloc[0]
        flag_slope = np.polyfit(range(len(flag)), flag["close"].values, 1)[0]

        if pole_drop > 0.03 and 0.003 < flag_retrace < 0.015 and flag_slope > 0:
            pole_size = pole["close"].iloc[0] - pole["close"].iloc[-1]
            target = df["close"].iloc[-1] - pole_size
            stop = flag["high"].max()
            return ChartPattern("Bear Flag", "SELL", 0.80, target, stop,
                                f"Bear flag. Target {target:.2f}")
        return ChartPattern("Bear Flag", "SELL", 0, None, None, "", detected=False)

    # ── Cup and Handle ────────────────────────────────────────────────────

    def cup_and_handle(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 40:
            return None
        cup = df.tail(40).head(30)
        handle = df.tail(10)

        cup_left = cup["close"].iloc[0]
        cup_bottom = cup["close"].min()
        cup_right = cup["close"].iloc[-1]
        handle_low = handle["close"].min()

        is_cup = (abs(cup_left - cup_right) / cup_left < 0.03) and \
                 ((cup_left - cup_bottom) / cup_left > 0.05)
        is_handle = (handle_low > cup_bottom) and (handle_low > cup_right * 0.95)

        if is_cup and is_handle:
            ltp = df["close"].iloc[-1]
            target = ltp + (cup_left - cup_bottom)
            return ChartPattern("Cup & Handle", "BUY", 0.82, target, handle_low,
                                f"Cup & Handle forming. Target {target:.2f}")
        return ChartPattern("Cup & Handle", "BUY", 0, None, None, "", detected=False)

    # ── Rounding Bottom ───────────────────────────────────────────────────

    def rounding_bottom(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 30:
            return None
        lows = df.tail(30)["low"].values
        x = np.arange(len(lows))
        coeffs = np.polyfit(x, lows, 2)
        # Positive quadratic coefficient = concave up = rounding bottom
        if coeffs[0] > 0:
            return ChartPattern("Rounding Bottom", "BUY", 0.70, None, lows.min(),
                                "Rounding bottom forming — gradual reversal pattern")
        return ChartPattern("Rounding Bottom", "BUY", 0, None, None, "", detected=False)

    # ── Rising Wedge ──────────────────────────────────────────────────────

    def rising_wedge(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 15:
            return None
        last = df.tail(15)
        high_slope = np.polyfit(range(15), last["high"].values, 1)[0]
        low_slope = np.polyfit(range(15), last["low"].values, 1)[0]

        if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
            return ChartPattern("Rising Wedge", "SELL", 0.72, None, None,
                                "Rising wedge — converging highs and lows going up. Bearish reversal expected.")
        return ChartPattern("Rising Wedge", "SELL", 0, None, None, "", detected=False)

    # ── Falling Wedge ─────────────────────────────────────────────────────

    def falling_wedge(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 15:
            return None
        last = df.tail(15)
        high_slope = np.polyfit(range(15), last["high"].values, 1)[0]
        low_slope = np.polyfit(range(15), last["low"].values, 1)[0]

        if high_slope < 0 and low_slope < 0 and high_slope < low_slope:
            return ChartPattern("Falling Wedge", "BUY", 0.72, None, None,
                                "Falling wedge — converging lows more than highs. Bullish reversal expected.")
        return ChartPattern("Falling Wedge", "BUY", 0, None, None, "", detected=False)

    # ── Channel Up ────────────────────────────────────────────────────────

    def channel_up(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 20:
            return None
        last = df.tail(20)
        high_slope = np.polyfit(range(20), last["high"].values, 1)[0]
        low_slope = np.polyfit(range(20), last["low"].values, 1)[0]

        if high_slope > 0 and low_slope > 0 and abs(high_slope - low_slope) / abs(high_slope) < 0.3:
            return ChartPattern("Channel Up", "BUY", 0.68, None, last["low"].min(),
                                "Ascending channel — buy near lower channel line")
        return ChartPattern("Channel Up", "BUY", 0, None, None, "", detected=False)

    # ── Channel Down ──────────────────────────────────────────────────────

    def channel_down(self, df: pd.DataFrame) -> ChartPattern | None:
        if len(df) < 20:
            return None
        last = df.tail(20)
        high_slope = np.polyfit(range(20), last["high"].values, 1)[0]
        low_slope = np.polyfit(range(20), last["low"].values, 1)[0]

        if high_slope < 0 and low_slope < 0 and abs(high_slope - low_slope) / abs(low_slope) < 0.3:
            return ChartPattern("Channel Down", "SELL", 0.68, None, last["high"].max(),
                                "Descending channel — sell near upper channel line")
        return ChartPattern("Channel Down", "SELL", 0, None, None, "", detected=False)

    # ── Opening Range Breakout ────────────────────────────────────────────

    def orb(self, df: pd.DataFrame) -> ChartPattern | None:
        """
        ORB: First 15-minute bar defines range.
        Breakout above = BUY, below = SELL.
        """
        if len(df) < 2:
            return None
        orb_bar = df.iloc[0]
        orb_high = orb_bar["high"]
        orb_low = orb_bar["low"]
        ltp = df["close"].iloc[-1]

        if ltp > orb_high:
            target = orb_high + (orb_high - orb_low)
            return ChartPattern("ORB Breakout", "BUY", 0.77, target, orb_low,
                                f"ORB breakout above {orb_high:.2f}. Target {target:.2f}")
        elif ltp < orb_low:
            target = orb_low - (orb_high - orb_low)
            return ChartPattern("ORB Breakdown", "SELL", 0.77, target, orb_high,
                                f"ORB breakdown below {orb_low:.2f}. Target {target:.2f}")
        return ChartPattern("ORB", "NEUTRAL", 0, None, None, "", detected=False)


chart_detector = ChartPatternDetector()

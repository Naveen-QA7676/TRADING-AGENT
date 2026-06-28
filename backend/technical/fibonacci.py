"""
Fibonacci retracement and extension levels.
Auto-detects the most recent swing for level placement.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from backend.technical.market_structure import market_structure_analyzer


@dataclass
class FibLevel:
    ratio: float
    price: float
    label: str
    is_support: bool
    is_resistance: bool


class FibonacciEngine:
    RETRACEMENT_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    EXTENSION_LEVELS = [1.272, 1.414, 1.618, 2.0, 2.618]

    def compute(self, swing_high: float, swing_low: float, trend: str) -> list[FibLevel]:
        """
        Compute retracement + extension from a swing.
        trend: "UP" = bullish swing (low → high), "DOWN" = bearish swing (high → low)
        """
        diff = swing_high - swing_low
        levels = []

        # Retracements
        for ratio in self.RETRACEMENT_LEVELS:
            if trend == "UP":
                price = swing_high - (ratio * diff)
                is_sup = ratio > 0.3  # meaningful retracement = support
                is_res = False
            else:
                price = swing_low + (ratio * diff)
                is_sup = False
                is_res = ratio > 0.3

            levels.append(FibLevel(
                ratio=ratio,
                price=round(price, 2),
                label=f"Fib {ratio:.3f}" if ratio not in [0.0, 1.0] else ("Swing High" if ratio == 1.0 else "Swing Low"),
                is_support=is_sup,
                is_resistance=is_res,
            ))

        # Extensions
        for ratio in self.EXTENSION_LEVELS:
            if trend == "UP":
                price = swing_low + (ratio * diff)
            else:
                price = swing_high - (ratio * diff)
            levels.append(FibLevel(
                ratio=ratio,
                price=round(price, 2),
                label=f"Fib Ext {ratio:.3f}",
                is_support=False,
                is_resistance=trend == "UP",
            ))

        return sorted(levels, key=lambda x: x.price)

    def auto_levels(self, df: pd.DataFrame) -> list[FibLevel]:
        """Auto-detect swing and compute Fibonacci levels."""
        swings = market_structure_analyzer.find_swing_points(df, lookback=3)
        highs = [s for s in swings if s.swing_type == "HIGH"]
        lows = [s for s in swings if s.swing_type == "LOW"]

        if not highs or not lows:
            return []

        last_high = highs[-1]
        last_low = lows[-1]

        if last_high.index > last_low.index:
            # Most recent move was DOWN from high → bearish fib
            return self.compute(last_high.price, last_low.price, "DOWN")
        else:
            # Most recent move was UP from low → bullish fib
            return self.compute(last_high.price, last_low.price, "UP")

    def nearest_fib_support(self, levels: list[FibLevel], price: float) -> FibLevel | None:
        supports = [l for l in levels if l.price < price and l.is_support]
        return max(supports, key=lambda x: x.price) if supports else None

    def nearest_fib_resistance(self, levels: list[FibLevel], price: float) -> FibLevel | None:
        resistances = [l for l in levels if l.price > price and l.is_resistance]
        return min(resistances, key=lambda x: x.price) if resistances else None


fib_engine = FibonacciEngine()

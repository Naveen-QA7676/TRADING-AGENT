"""
Cumulative Volume Delta (CVD) — tracks the running sum of (buy_vol - sell_vol).
Rising CVD with rising price = strong bullish trend.
Falling CVD with rising price = bearish divergence (smart money distributing).
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from collections import deque
from loguru import logger


@dataclass
class DeltaReading:
    delta: float              # current bar delta (buy_vol - sell_vol)
    cvd: float                # cumulative delta
    cvd_ema: float            # smoothed CVD
    divergence: str           # "NONE", "BULLISH_DIV", "BEARISH_DIV"
    trend: str                # "BUYERS_DOMINANT", "SELLERS_DOMINANT", "BALANCED"
    strength: float           # 0–1
    description: str


class CVDEngine:
    """
    Cumulative Volume Delta engine for order flow analysis.
    Input: footprint bars (from TickAggregator) with buy_vol / sell_vol
    """

    def __init__(self, history_size: int = 200):
        self._bars: deque = deque(maxlen=history_size)
        self._cvd_history: deque = deque(maxlen=history_size)
        self._cvd: float = 0.0

    def update(self, bar: dict) -> DeltaReading:
        """Process a completed footprint bar and return CVD reading."""
        delta = bar.get("buy_vol", 0) - bar.get("sell_vol", 0)
        self._cvd += delta
        self._bars.append(bar)
        self._cvd_history.append(self._cvd)

        return self._compute_reading(bar["close"], delta)

    def _compute_reading(self, price: float, delta: float) -> DeltaReading:
        cvd_arr = np.array(list(self._cvd_history))
        if len(cvd_arr) < 5:
            return DeltaReading(delta, self._cvd, self._cvd, "NONE", "BALANCED", 0.5, "Insufficient data")

        # EMA of CVD
        alpha = 2 / (10 + 1)
        cvd_ema = cvd_arr[0]
        for v in cvd_arr[1:]:
            cvd_ema = alpha * v + (1 - alpha) * cvd_ema

        # Trend (recent 10 bars)
        recent = cvd_arr[-10:] if len(cvd_arr) >= 10 else cvd_arr
        cvd_slope = np.polyfit(range(len(recent)), recent, 1)[0]

        if cvd_slope > 0:
            trend = "BUYERS_DOMINANT"
            strength = min(1.0, abs(cvd_slope) / (abs(recent).mean() + 1e-9) * 10)
        elif cvd_slope < 0:
            trend = "SELLERS_DOMINANT"
            strength = min(1.0, abs(cvd_slope) / (abs(recent).mean() + 1e-9) * 10)
        else:
            trend = "BALANCED"
            strength = 0.3

        # Divergence detection
        bars = list(self._bars)[-10:]
        if len(bars) >= 5:
            price_arr = np.array([b["close"] for b in bars])
            cvd_recent = np.array(list(self._cvd_history)[-10:])

            price_slope = np.polyfit(range(len(price_arr)), price_arr, 1)[0]
            cvd_sl = np.polyfit(range(len(cvd_recent)), cvd_recent, 1)[0]

            if price_slope > 0 and cvd_sl < 0:
                divergence = "BEARISH_DIV"
                desc = "BEARISH DIVERGENCE: Price rising but CVD falling — institutional distribution!"
            elif price_slope < 0 and cvd_sl > 0:
                divergence = "BULLISH_DIV"
                desc = "BULLISH DIVERGENCE: Price falling but CVD rising — smart money accumulating!"
            else:
                divergence = "NONE"
                if trend == "BUYERS_DOMINANT":
                    desc = f"CVD +{self._cvd:,.0f} rising — buyers dominating, trend valid"
                elif trend == "SELLERS_DOMINANT":
                    desc = f"CVD {self._cvd:,.0f} falling — sellers dominating"
                else:
                    desc = f"CVD {self._cvd:,.0f} — balanced order flow"
        else:
            divergence = "NONE"
            desc = f"CVD: {self._cvd:,.0f}"

        return DeltaReading(
            delta=round(delta, 0),
            cvd=round(self._cvd, 0),
            cvd_ema=round(cvd_ema, 0),
            divergence=divergence,
            trend=trend,
            strength=round(strength, 2),
            description=desc,
        )

    def compute_from_dataframe(self, df_with_delta: pd.DataFrame) -> DeltaReading:
        """Compute CVD from a DataFrame that has buy_vol / sell_vol columns."""
        if "buy_vol" not in df_with_delta.columns or "sell_vol" not in df_with_delta.columns:
            return DeltaReading(0, 0, 0, "NONE", "BALANCED", 0.5, "No volume data")

        self._cvd = 0
        self._bars.clear()
        self._cvd_history.clear()

        latest = DeltaReading(0, 0, 0, "NONE", "BALANCED", 0.5, "")
        for _, row in df_with_delta.iterrows():
            bar = {
                "buy_vol": row.get("buy_vol", 0),
                "sell_vol": row.get("sell_vol", 0),
                "close": row.get("close", 0),
            }
            latest = self.update(bar)
        return latest

    def get_cvd(self) -> float:
        return self._cvd

    def get_history(self) -> list[float]:
        return list(self._cvd_history)


# Per-symbol CVD engines
_cvd_engines: dict[str, CVDEngine] = {}


def get_cvd_engine(symbol: str) -> CVDEngine:
    if symbol not in _cvd_engines:
        _cvd_engines[symbol] = CVDEngine()
    return _cvd_engines[symbol]

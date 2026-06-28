"""
Spread Monitor — tracks bid-ask spread over time to detect:
- Liquidity conditions (tight spread = good)
- Spread widening = uncertainty/risk
- Pre-manipulation indicators (sudden spread expansion)
"""

from collections import deque
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class SpreadStatus:
    current_spread: float
    current_spread_pct: float
    avg_spread: float
    spread_ratio: float       # current / average
    status: str               # "TIGHT", "NORMAL", "WIDE", "VERY_WIDE"
    is_tradeable: bool
    description: str


class SpreadMonitor:

    def __init__(self, window: int = 50):
        self._history: deque = deque(maxlen=window)

    def update(self, spread: float, spread_pct: float) -> SpreadStatus:
        self._history.append(spread_pct)

        if len(self._history) < 3:
            return SpreadStatus(
                current_spread=spread, current_spread_pct=spread_pct,
                avg_spread=spread_pct, spread_ratio=1.0,
                status="NORMAL", is_tradeable=True,
                description="Insufficient history"
            )

        arr = np.array(self._history)
        avg = arr.mean()
        ratio = spread_pct / avg if avg > 0 else 1.0

        if spread_pct <= 0.02:
            status = "TIGHT"
            is_tradeable = True
        elif spread_pct <= 0.05:
            status = "NORMAL"
            is_tradeable = True
        elif spread_pct <= 0.15:
            status = "WIDE"
            is_tradeable = True   # can trade, but expect slippage
        else:
            status = "VERY_WIDE"
            is_tradeable = False  # avoid trading

        if ratio > 3.0:
            desc = f"SPREAD ALERT: {spread_pct:.3f}% ({ratio:.1f}× normal). Unusual activity."
        elif ratio > 2.0:
            desc = f"Spread widening to {spread_pct:.3f}% ({ratio:.1f}× avg). Exercise caution."
        else:
            desc = f"Spread {spread_pct:.3f}% — {status}"

        return SpreadStatus(
            current_spread=spread,
            current_spread_pct=spread_pct,
            avg_spread=round(avg, 4),
            spread_ratio=round(ratio, 2),
            status=status,
            is_tradeable=is_tradeable,
            description=desc,
        )


# Per-symbol spread monitors
_spread_monitors: dict[str, SpreadMonitor] = {}


def get_spread_monitor(symbol: str) -> SpreadMonitor:
    if symbol not in _spread_monitors:
        _spread_monitors[symbol] = SpreadMonitor()
    return _spread_monitors[symbol]

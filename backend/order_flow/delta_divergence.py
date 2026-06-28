"""
Delta Divergence detector — identifies when price and CVD/delta diverge.
Critical institutional signal: price going up but sellers in control = trap.
"""

import numpy as np
from dataclasses import dataclass
from loguru import logger


@dataclass
class DivergenceSignal:
    detected: bool
    divergence_type: str    # "BULLISH", "BEARISH", "NONE"
    strength: float         # 0–1
    message: str
    action: str             # "WATCH_FOR_REVERSAL", "CAUTION", "NONE"


class DeltaDivergenceDetector:

    def detect(
        self,
        price_history: list[float],
        cvd_history: list[float],
        delta_history: list[float],
        lookback: int = 10,
    ) -> DivergenceSignal:
        if len(price_history) < lookback or len(cvd_history) < lookback:
            return DivergenceSignal(False, "NONE", 0, "Insufficient data", "NONE")

        prices = np.array(price_history[-lookback:])
        cvds = np.array(cvd_history[-lookback:])
        deltas = np.array(delta_history[-lookback:]) if delta_history else cvds

        x = np.arange(lookback)
        price_slope = np.polyfit(x, prices, 1)[0]
        cvd_slope = np.polyfit(x, cvds, 1)[0]

        price_up = price_slope > 0
        cvd_up = cvd_slope > 0

        # Bearish divergence: price going up, CVD going down
        if price_up and not cvd_up:
            strength = min(1.0, abs(cvd_slope) / (np.std(cvds) + 1e-9))
            return DivergenceSignal(
                detected=True,
                divergence_type="BEARISH",
                strength=strength,
                message=("BEARISH DIVERGENCE: Price making higher highs but CVD declining. "
                         "Institutions distributing into retail buying. HIGH RISK for longs."),
                action="WATCH_FOR_REVERSAL",
            )

        # Bullish divergence: price going down, CVD going up
        if not price_up and cvd_up:
            strength = min(1.0, abs(cvd_slope) / (np.std(cvds) + 1e-9))
            return DivergenceSignal(
                detected=True,
                divergence_type="BULLISH",
                strength=strength,
                message=("BULLISH DIVERGENCE: Price falling but CVD rising. "
                         "Smart money accumulating. Reversal likely soon."),
                action="WATCH_FOR_REVERSAL",
            )

        # Check recent delta exhaustion (last few bars delta reversing)
        if len(deltas) >= 3:
            recent_sum = deltas[-3:].sum()
            if price_up and recent_sum < 0:
                return DivergenceSignal(
                    detected=True,
                    divergence_type="BEARISH",
                    strength=0.6,
                    message="Delta exhaustion: price up but recent ticks seller-dominated. Caution.",
                    action="CAUTION",
                )
            elif not price_up and recent_sum > 0:
                return DivergenceSignal(
                    detected=True,
                    divergence_type="BULLISH",
                    strength=0.6,
                    message="Delta exhaustion: price down but recent ticks buyer-dominated. Watch for reversal.",
                    action="CAUTION",
                )

        return DivergenceSignal(
            detected=False, divergence_type="NONE", strength=0,
            message="No divergence detected — price and delta aligned",
            action="NONE",
        )


delta_divergence_detector = DeltaDivergenceDetector()

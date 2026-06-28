"""
Slippage Estimator — predicts fill slippage based on:
- Order size vs available liquidity
- Current spread
- Historical slippage data
- Market impact model (Almgren-Chriss simplified)
"""

import math
from dataclasses import dataclass
from loguru import logger


@dataclass
class SlippageEstimate:
    expected_slippage_pct: float    # e.g. 0.05 = 0.05%
    expected_slippage_inr: float    # in rupees per share
    confidence: str                 # "LOW", "MEDIUM", "HIGH"
    recommendation: str
    is_acceptable: bool             # below threshold


class SlippageEstimator:

    def estimate(
        self,
        order_qty: int,
        ltp: float,
        spread_pct: float,
        bid_total: int,
        ask_total: int,
        direction: str,             # "BUY" or "SELL"
        avg_daily_vol: int = 100000,
    ) -> SlippageEstimate:
        """
        Simplified market impact estimate.
        Based on Kyle's lambda model: price impact ∝ order_size / avg_volume.
        """
        order_value = order_qty * ltp

        # Participation rate
        participation = order_qty / max(1, avg_daily_vol / 375)  # 375 min/day

        # Half-spread cost
        half_spread = spread_pct / 2

        # Market impact (simplified Almgren-Chriss)
        # Temporary impact: η × σ × (Q / V)^0.6
        sigma = 0.015  # assume 1.5% daily vol
        impact = sigma * (participation ** 0.6)

        total_slippage_pct = half_spread + impact
        slippage_inr = total_slippage_pct / 100 * ltp

        # Check available liquidity
        available = ask_total if direction == "BUY" else bid_total
        if available > 0 and order_qty > available * 0.5:
            total_slippage_pct *= 1.5
            slippage_inr = total_slippage_pct / 100 * ltp
            confidence = "LOW"
            rec = "Order size consumes >50% of Level 1 — split into smaller orders or use iceberg"
        elif participation > 0.1:
            confidence = "MEDIUM"
            rec = f"Participation rate {participation:.1%} — expect {total_slippage_pct:.3f}% slippage"
        else:
            confidence = "HIGH"
            rec = f"Slippage estimate {total_slippage_pct:.3f}% — acceptable for this size"

        is_acceptable = total_slippage_pct <= 0.1  # < 0.1% = acceptable

        return SlippageEstimate(
            expected_slippage_pct=round(total_slippage_pct, 4),
            expected_slippage_inr=round(slippage_inr, 2),
            confidence=confidence,
            recommendation=rec,
            is_acceptable=is_acceptable,
        )


slippage_estimator = SlippageEstimator()

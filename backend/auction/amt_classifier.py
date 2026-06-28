"""
Auction Market Theory (AMT) Classifier.
Classifies each trading session as:
- Balanced: price explores a range, no directional conviction
- Imbalanced: directional excess, one side dominates
Also detects: trend day, range day, gap day, neutral day types.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from loguru import logger


@dataclass
class AuctionClassification:
    session_type: str          # "TREND_DAY", "RANGE_DAY", "GAP_DAY", "NEUTRAL", "DOUBLE_DISTRIBUTION"
    balance_state: str         # "BALANCED", "IMBALANCED_UP", "IMBALANCED_DOWN"
    is_initiative: bool        # True = aggressive new business, False = responsive
    value_area_overlap: float  # % overlap with previous day's value area (0 = rotational, 100 = very close)
    excess_high: bool          # spike at top (selling tail)
    excess_low: bool           # spike at bottom (buying tail)
    opening_type: str          # "GAP_UP", "GAP_DOWN", "OPEN_DRIVE", "OPEN_TEST", "OPEN_AUCTION"
    context: str               # narrative explanation
    trade_bias: str            # "BUY", "SELL", "NEUTRAL"


class AMTClassifier:

    def classify_session(
        self,
        df_today: pd.DataFrame,
        prev_vah: float,
        prev_val: float,
        prev_poc: float,
        prev_close: float,
    ) -> AuctionClassification:
        """
        Classify today's session using Auction Market Theory principles.
        """
        if df_today is None or len(df_today) < 3:
            return AuctionClassification(
                session_type="UNKNOWN", balance_state="BALANCED",
                is_initiative=False, value_area_overlap=50,
                excess_high=False, excess_low=False,
                opening_type="OPEN_AUCTION", context="Insufficient data",
                trade_bias="NEUTRAL"
            )

        today_high = df_today["high"].max()
        today_low = df_today["low"].min()
        today_open = df_today["open"].iloc[0]
        today_close = df_today["close"].iloc[-1]
        today_range = today_high - today_low

        # Opening type
        gap = today_open - prev_close
        gap_pct = gap / prev_close if prev_close > 0 else 0

        if gap_pct > 0.005:
            opening_type = "GAP_UP"
        elif gap_pct < -0.005:
            opening_type = "GAP_DOWN"
        else:
            # First 15-30 min behaviour
            first_bars = df_today.head(6)
            first_range = first_bars["high"].max() - first_bars["low"].min()
            if first_range < today_range * 0.15 and today_close > today_open:
                opening_type = "OPEN_DRIVE"
            elif abs(today_open - prev_close) < prev_close * 0.001:
                opening_type = "OPEN_TEST"
            else:
                opening_type = "OPEN_AUCTION"

        # Value area overlap with previous day
        overlap_low = max(today_low, prev_val) if prev_val else today_low
        overlap_high = min(today_high, prev_vah) if prev_vah else today_high
        overlap = max(0, overlap_high - overlap_low)
        prev_va_size = (prev_vah - prev_val) if prev_vah and prev_val and prev_vah > prev_val else 1
        va_overlap_pct = min(100, (overlap / prev_va_size) * 100) if prev_va_size > 0 else 0

        # Balance state: range covered vs expected
        mid = (today_high + today_low) / 2
        close_pct = (today_close - today_low) / today_range if today_range > 0 else 0.5

        if close_pct > 0.75:
            balance_state = "IMBALANCED_UP"
        elif close_pct < 0.25:
            balance_state = "IMBALANCED_DOWN"
        else:
            balance_state = "BALANCED"

        # Excess (tails) — spikes that get rejected
        body_high = max(df_today["open"].iloc[0], df_today["close"].iloc[-1])
        body_low = min(df_today["open"].iloc[0], df_today["close"].iloc[-1])
        upper_tail = today_high - body_high
        lower_tail = body_low - today_low
        excess_high = upper_tail > today_range * 0.15
        excess_low = lower_tail > today_range * 0.15

        # Session type classification
        # Trend day: > 75% of range in one direction, close near extreme
        is_trend_up = close_pct > 0.80 and opening_type in ["OPEN_DRIVE", "GAP_UP"]
        is_trend_down = close_pct < 0.20 and opening_type in ["OPEN_DRIVE", "GAP_DOWN"]

        # Range day: multiple rotations, close near mid
        is_range = 0.35 <= close_pct <= 0.65 and va_overlap_pct > 50

        # Gap day: opened outside previous value area
        is_gap = opening_type in ["GAP_UP", "GAP_DOWN"]

        # Double distribution: two distinct volume clusters
        is_double_dist = va_overlap_pct < 20 and balance_state == "BALANCED"

        if is_trend_up:
            session_type = "TREND_DAY_UP"
        elif is_trend_down:
            session_type = "TREND_DAY_DOWN"
        elif is_gap:
            session_type = "GAP_DAY"
        elif is_double_dist:
            session_type = "DOUBLE_DISTRIBUTION"
        elif is_range:
            session_type = "RANGE_DAY"
        else:
            session_type = "NEUTRAL_DAY"

        # Initiative vs Responsive
        # Initiative: price extending beyond previous session's extremes
        # Responsive: price returning to previous session's value area
        if today_high > prev_vah or today_low < prev_val:
            is_initiative = True
        else:
            is_initiative = False

        # Trade bias
        if balance_state == "IMBALANCED_UP" and is_initiative:
            trade_bias = "BUY"
        elif balance_state == "IMBALANCED_DOWN" and is_initiative:
            trade_bias = "SELL"
        elif is_range:
            trade_bias = "NEUTRAL"
        elif close_pct > 0.6:
            trade_bias = "BUY"
        elif close_pct < 0.4:
            trade_bias = "SELL"
        else:
            trade_bias = "NEUTRAL"

        # Context narrative
        context_parts = [
            f"Session type: {session_type}",
            f"Opening: {opening_type} (gap {gap_pct:+.2%})",
            f"VA overlap with yesterday: {va_overlap_pct:.0f}%",
            f"Close position in range: {close_pct:.0f}% (top of range = 100%)",
            f"{'Initiative (new territory)' if is_initiative else 'Responsive (within old VA)'}",
            f"Excess: top={'Yes' if excess_high else 'No'}, bottom={'Yes' if excess_low else 'No'}",
        ]

        return AuctionClassification(
            session_type=session_type,
            balance_state=balance_state,
            is_initiative=is_initiative,
            value_area_overlap=round(va_overlap_pct, 1),
            excess_high=excess_high,
            excess_low=excess_low,
            opening_type=opening_type,
            context=" | ".join(context_parts),
            trade_bias=trade_bias,
        )


amt_classifier = AMTClassifier()

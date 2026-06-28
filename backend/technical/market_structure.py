"""
Market Structure Analysis: HH/HL/LH/LL detection, Break of Structure (BoS),
Change of Character (ChoCH), trend classification, swing highs/lows.
Smart Money Concepts: Order Blocks, Fair Value Gaps (FVG), liquidity sweeps.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class SwingPoint:
    index: int
    price: float
    swing_type: str    # "HIGH" or "LOW"
    bar_time: str = ""


@dataclass
class MarketStructure:
    trend: str                          # "UP", "DOWN", "SIDEWAYS"
    structure_type: str                 # "HH_HL", "LH_LL", "BoS_UP", "ChoCH_UP", etc.
    last_swing_high: float = 0.0
    last_swing_low: float = 0.0
    prev_swing_high: float = 0.0
    prev_swing_low: float = 0.0
    bos_detected: bool = False          # Break of Structure
    choch_detected: bool = False        # Change of Character
    bos_level: float = 0.0
    choch_level: float = 0.0
    description: str = ""
    strength: float = 0.5               # 0–1 how clear the structure is


@dataclass
class OrderBlock:
    """SMC Order Block — institutional footprint."""
    direction: str       # "BULLISH" or "BEARISH"
    high: float
    low: float
    origin_index: int
    is_valid: bool = True
    touch_count: int = 0


@dataclass
class FairValueGap:
    """Fair Value Gap (FVG) — imbalance between 3 candles."""
    direction: str    # "BULLISH" or "BEARISH"
    high: float
    low: float
    mid: float
    origin_index: int
    is_filled: bool = False


class MarketStructureAnalyzer:

    def find_swing_points(self, df: pd.DataFrame, lookback: int = 3) -> list[SwingPoint]:
        """
        Find swing highs and lows using a rolling window pivot algorithm.
        A swing high has `lookback` bars lower on both sides.
        """
        swings = []
        highs = df["high"].values
        lows = df["low"].values

        for i in range(lookback, len(df) - lookback):
            # Swing High
            if all(highs[i] > highs[i - j] for j in range(1, lookback + 1)) and \
               all(highs[i] > highs[i + j] for j in range(1, lookback + 1)):
                swings.append(SwingPoint(index=i, price=highs[i], swing_type="HIGH"))
            # Swing Low
            if all(lows[i] < lows[i - j] for j in range(1, lookback + 1)) and \
               all(lows[i] < lows[i + j] for j in range(1, lookback + 1)):
                swings.append(SwingPoint(index=i, price=lows[i], swing_type="LOW"))

        return swings

    def analyze(self, df: pd.DataFrame, lookback: int = 3) -> MarketStructure:
        """
        Full market structure analysis: HH/HL/LH/LL → BoS/ChoCH detection.
        """
        ms = MarketStructure(trend="SIDEWAYS", structure_type="UNDEFINED")

        swings = self.find_swing_points(df, lookback)
        if len(swings) < 4:
            ms.description = "Insufficient swing points for structure analysis"
            return ms

        highs = [s for s in swings if s.swing_type == "HIGH"]
        lows = [s for s in swings if s.swing_type == "LOW"]

        if len(highs) < 2 or len(lows) < 2:
            ms.description = "Not enough swing highs/lows"
            return ms

        h1, h2 = highs[-2], highs[-1]
        l1, l2 = lows[-2], lows[-1]

        ms.prev_swing_high = h1.price
        ms.last_swing_high = h2.price
        ms.prev_swing_low = l1.price
        ms.last_swing_low = l2.price

        is_hh = h2.price > h1.price
        is_hl = l2.price > l1.price
        is_lh = h2.price < h1.price
        is_ll = l2.price < l1.price

        # Trend classification
        if is_hh and is_hl:
            ms.trend = "UP"
            ms.structure_type = "HH_HL"
            ms.strength = 0.85
            ms.description = f"Uptrend: HH {h2.price:.2f} > {h1.price:.2f} | HL {l2.price:.2f} > {l1.price:.2f}"
        elif is_lh and is_ll:
            ms.trend = "DOWN"
            ms.structure_type = "LH_LL"
            ms.strength = 0.85
            ms.description = f"Downtrend: LH {h2.price:.2f} < {h1.price:.2f} | LL {l2.price:.2f} < {l1.price:.2f}"
        elif is_hh and is_ll:
            ms.trend = "SIDEWAYS"
            ms.structure_type = "EXPANDING"
            ms.strength = 0.3
            ms.description = "Expanding range — widening volatility"
        elif is_lh and is_hl:
            ms.trend = "SIDEWAYS"
            ms.structure_type = "CONTRACTING"
            ms.strength = 0.3
            ms.description = "Contracting range — compression, breakout pending"
        else:
            ms.trend = "SIDEWAYS"
            ms.structure_type = "MIXED"
            ms.strength = 0.2
            ms.description = "Mixed structure — no clear trend"

        # Break of Structure (BoS) — continuation
        ltp = df["close"].iloc[-1]
        if ms.trend == "UP" and ltp > h2.price:
            ms.bos_detected = True
            ms.bos_level = h2.price
            ms.description += f" | BoS UP at {h2.price:.2f} — bullish continuation"
        elif ms.trend == "DOWN" and ltp < l2.price:
            ms.bos_detected = True
            ms.bos_level = l2.price
            ms.description += f" | BoS DOWN at {l2.price:.2f} — bearish continuation"

        # Change of Character (ChoCH) — reversal signal
        if ms.trend == "UP" and ltp < l2.price:
            ms.choch_detected = True
            ms.choch_level = l2.price
            ms.trend = "REVERSAL_DOWN"
            ms.description += f" | ChoCH! Price broke HL at {l2.price:.2f} — reversal warning"
        elif ms.trend == "DOWN" and ltp > h2.price:
            ms.choch_detected = True
            ms.choch_level = h2.price
            ms.trend = "REVERSAL_UP"
            ms.description += f" | ChoCH! Price broke LH at {h2.price:.2f} — reversal warning"

        return ms

    def find_order_blocks(self, df: pd.DataFrame, lookback: int = 20) -> list[OrderBlock]:
        """
        Identify Order Blocks (OB) — last opposite-coloured candle before a strong impulse.
        Bullish OB: last bearish candle before strong bullish impulse.
        Bearish OB: last bullish candle before strong bearish impulse.
        """
        obs = []
        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values

        for i in range(2, min(len(df) - 1, lookback)):
            # Detect strong impulse (body > 1.5× average body)
            body = abs(closes[i] - opens[i])
            avg_body = np.mean([abs(closes[j] - opens[j]) for j in range(max(0, i-10), i)])
            if avg_body == 0:
                continue
            is_strong = body > 1.5 * avg_body

            if not is_strong:
                continue

            # Bullish impulse → look for last bearish candle before it
            if closes[i] > opens[i]:  # bullish candle
                for j in range(i - 1, max(0, i - 5), -1):
                    if closes[j] < opens[j]:  # bearish candle
                        obs.append(OrderBlock(
                            direction="BULLISH",
                            high=highs[j],
                            low=lows[j],
                            origin_index=j,
                        ))
                        break

            # Bearish impulse → look for last bullish candle before it
            elif closes[i] < opens[i]:  # bearish candle
                for j in range(i - 1, max(0, i - 5), -1):
                    if closes[j] > opens[j]:  # bullish candle
                        obs.append(OrderBlock(
                            direction="BEARISH",
                            high=highs[j],
                            low=lows[j],
                            origin_index=j,
                        ))
                        break

        # Mark OBs that have been tested (price returned to them)
        ltp = closes[-1]
        for ob in obs:
            if ob.direction == "BULLISH" and ob.low <= ltp <= ob.high:
                ob.touch_count += 1
            elif ob.direction == "BEARISH" and ob.low <= ltp <= ob.high:
                ob.touch_count += 1

        return obs[-10:]  # keep last 10

    def find_fvg(self, df: pd.DataFrame) -> list[FairValueGap]:
        """
        Fair Value Gap (FVG) — 3-candle imbalance.
        Bullish FVG: candle[i-1].low > candle[i+1].high
        Bearish FVG: candle[i-1].high < candle[i+1].low
        """
        fvgs = []
        highs = df["high"].values
        lows = df["low"].values

        for i in range(1, len(df) - 1):
            # Bullish FVG
            if lows[i - 1] > highs[i + 1]:
                gap_high = lows[i - 1]
                gap_low = highs[i + 1]
                fvgs.append(FairValueGap(
                    direction="BULLISH",
                    high=gap_high,
                    low=gap_low,
                    mid=(gap_high + gap_low) / 2,
                    origin_index=i,
                ))
            # Bearish FVG
            elif highs[i - 1] < lows[i + 1]:
                gap_high = lows[i + 1]
                gap_low = highs[i - 1]
                fvgs.append(FairValueGap(
                    direction="BEARISH",
                    high=gap_high,
                    low=gap_low,
                    mid=(gap_high + gap_low) / 2,
                    origin_index=i,
                ))

        # Check if filled
        ltp = df["close"].iloc[-1]
        for fvg in fvgs:
            if fvg.direction == "BULLISH" and ltp < fvg.low:
                fvg.is_filled = True
            elif fvg.direction == "BEARISH" and ltp > fvg.high:
                fvg.is_filled = True

        return [f for f in fvgs[-20:] if not f.is_filled]


market_structure_analyzer = MarketStructureAnalyzer()

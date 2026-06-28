"""
Dynamic Support & Resistance detection using multiple methods:
- Swing high/low clustering
- Volume-weighted price clusters
- Previous Day High/Low (PDH/PDL)
- Weekly/Monthly levels
- Round number levels
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from loguru import logger


@dataclass
class Level:
    price: float
    level_type: str       # "SUPPORT", "RESISTANCE", "PDH", "PDL", "WEEKLY_HIGH", "ROUND"
    strength: float       # 0–1
    touch_count: int = 1
    description: str = ""


class SupportResistanceEngine:

    def find_levels(
        self,
        df: pd.DataFrame,
        prev_day_high: float = None,
        prev_day_low: float = None,
        prev_week_high: float = None,
        prev_week_low: float = None,
        tolerance_pct: float = 0.003,   # 0.3% cluster tolerance
    ) -> list[Level]:
        levels = []

        # 1. Swing-based levels
        swing_levels = self._swing_levels(df)
        levels.extend(swing_levels)

        # 2. Volume-cluster levels
        vol_levels = self._volume_cluster_levels(df)
        levels.extend(vol_levels)

        # 3. Previous day levels
        if prev_day_high:
            levels.append(Level(prev_day_high, "PDH", 0.85, description="Previous Day High"))
        if prev_day_low:
            levels.append(Level(prev_day_low, "PDL", 0.85, description="Previous Day Low"))

        # 4. Weekly levels
        if prev_week_high:
            levels.append(Level(prev_week_high, "WEEKLY_HIGH", 0.9, description="Previous Week High"))
        if prev_week_low:
            levels.append(Level(prev_week_low, "WEEKLY_LOW", 0.9, description="Previous Week Low"))

        # 5. Round number levels
        ltp = df["close"].iloc[-1]
        round_levels = self._round_number_levels(ltp, window=0.05)
        levels.extend(round_levels)

        # 6. Cluster nearby levels
        levels = self._cluster_levels(levels, tolerance_pct)

        # 7. Classify each level relative to current price
        for lv in levels:
            if lv.price > ltp:
                if lv.level_type not in ["PDH", "PDL", "WEEKLY_HIGH", "WEEKLY_LOW", "ROUND"]:
                    lv.level_type = "RESISTANCE"
            else:
                if lv.level_type not in ["PDH", "PDL", "WEEKLY_HIGH", "WEEKLY_LOW", "ROUND"]:
                    lv.level_type = "SUPPORT"

        levels.sort(key=lambda x: x.price)
        return levels

    def _swing_levels(self, df: pd.DataFrame, lookback: int = 3) -> list[Level]:
        levels = []
        highs = df["high"].values
        lows = df["low"].values

        for i in range(lookback, len(df) - lookback):
            if all(highs[i] >= highs[i - j] for j in range(1, lookback + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, lookback + 1)):
                levels.append(Level(
                    price=highs[i],
                    level_type="RESISTANCE",
                    strength=0.6,
                    description=f"Swing high at bar {i}"
                ))
            if all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, lookback + 1)):
                levels.append(Level(
                    price=lows[i],
                    level_type="SUPPORT",
                    strength=0.6,
                    description=f"Swing low at bar {i}"
                ))
        return levels

    def _volume_cluster_levels(self, df: pd.DataFrame, bins: int = 50) -> list[Level]:
        """Find price levels with disproportionately high volume (HVN)."""
        if "volume" not in df.columns or df["volume"].sum() == 0:
            return []

        price_min = df["low"].min()
        price_max = df["high"].max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        bin_vols = np.zeros(bins)

        for _, row in df.iterrows():
            typical = (row["high"] + row["low"] + row["close"]) / 3
            idx = np.searchsorted(bin_edges, typical) - 1
            idx = max(0, min(bins - 1, idx))
            bin_vols[idx] += row["volume"]

        avg_vol = bin_vols.mean()
        threshold = avg_vol * 1.5

        levels = []
        for i, vol in enumerate(bin_vols):
            if vol >= threshold:
                price = (bin_edges[i] + bin_edges[i + 1]) / 2
                strength = min(1.0, vol / (avg_vol * 3))
                levels.append(Level(
                    price=round(price, 2),
                    level_type="HVN",
                    strength=strength,
                    description=f"High Volume Node (vol={vol:.0f})"
                ))
        return levels

    def _round_number_levels(self, ltp: float, window: float = 0.05) -> list[Level]:
        """Round numbers act as psychological S/R."""
        levels = []
        step = 50 if ltp > 1000 else 10 if ltp > 200 else 5
        low = ltp * (1 - window)
        high = ltp * (1 + window)
        n = int(low // step)
        while n * step <= high:
            price = n * step
            if price > 0:
                levels.append(Level(
                    price=float(price),
                    level_type="ROUND",
                    strength=0.5,
                    description=f"Round number {price}"
                ))
            n += 1
        return levels

    def _cluster_levels(self, levels: list[Level], tolerance_pct: float) -> list[Level]:
        """Merge nearby levels into stronger clustered levels."""
        if not levels:
            return []
        levels.sort(key=lambda x: x.price)
        clustered = []
        current_group = [levels[0]]

        for lv in levels[1:]:
            ref_price = current_group[0].price
            if abs(lv.price - ref_price) / ref_price <= tolerance_pct:
                current_group.append(lv)
            else:
                merged = self._merge_group(current_group)
                clustered.append(merged)
                current_group = [lv]

        clustered.append(self._merge_group(current_group))
        return clustered

    def _merge_group(self, group: list[Level]) -> Level:
        avg_price = sum(l.price for l in group) / len(group)
        max_strength = max(l.strength for l in group)
        combined_strength = min(1.0, max_strength + (len(group) - 1) * 0.1)
        types = list(set(l.level_type for l in group))
        primary_type = max(group, key=lambda l: l.strength).level_type
        return Level(
            price=round(avg_price, 2),
            level_type=primary_type,
            strength=combined_strength,
            touch_count=len(group),
            description=f"Cluster ({', '.join(types)}) × {len(group)} touches"
        )

    def nearest_support(self, levels: list[Level], price: float) -> Level | None:
        supports = [l for l in levels if l.price < price]
        return max(supports, key=lambda x: x.price) if supports else None

    def nearest_resistance(self, levels: list[Level], price: float) -> Level | None:
        resistances = [l for l in levels if l.price > price]
        return min(resistances, key=lambda x: x.price) if resistances else None


sr_engine = SupportResistanceEngine()

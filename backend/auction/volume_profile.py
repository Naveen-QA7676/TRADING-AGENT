"""
Volume Profile engine: POC, VAH, VAL, HVN, LVN.
Implements TPO (Time Price Opportunity) logic and Value Area calculation.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class VolumeProfileResult:
    poc: float                  # Point of Control — highest volume price
    vah: float                  # Value Area High (70% of volume above POC)
    val: float                  # Value Area Low (70% of volume below POC)
    value_area_pct: float = 0.70

    hvn: list[float] = field(default_factory=list)   # High Volume Nodes
    lvn: list[float] = field(default_factory=list)   # Low Volume Nodes
    single_prints: list[float] = field(default_factory=list)  # thin areas = fast lanes

    total_volume: int = 0
    is_bullish_profile: bool = True   # majority of volume above or below POC

    distribution: pd.DataFrame = field(default_factory=pd.DataFrame)

    def summary(self) -> str:
        return (f"POC: {self.poc:.2f} | VAH: {self.vah:.2f} | VAL: {self.val:.2f} | "
                f"HVN: {len(self.hvn)} nodes | LVN: {len(self.lvn)} nodes | "
                f"Bias: {'BULLISH' if self.is_bullish_profile else 'BEARISH'}")


class VolumeProfileEngine:
    """
    Builds Volume Profile from OHLCV data.
    Value Area = 70% of total volume centered on POC.
    HVN = price levels with volume > 1.5× average.
    LVN = price levels with volume < 0.5× average (fast lanes for price to traverse).
    """

    def compute(
        self,
        df: pd.DataFrame,
        tick_size: float = 0.05,
        va_pct: float = 0.70,
        hvn_threshold: float = 1.5,
        lvn_threshold: float = 0.5,
    ) -> VolumeProfileResult:
        if df is None or len(df) < 5:
            return VolumeProfileResult(poc=0, vah=0, val=0)

        # Build price→volume distribution
        price_min = df["low"].min()
        price_max = df["high"].max()

        if price_min >= price_max:
            return VolumeProfileResult(poc=0, vah=0, val=0)

        num_bins = max(20, int((price_max - price_min) / tick_size))
        bins = np.linspace(price_min, price_max, num_bins + 1)
        bin_volumes = np.zeros(num_bins)

        for _, row in df.iterrows():
            vol = int(row["volume"])
            # Distribute vol over bar's H-L range
            low_idx = np.searchsorted(bins, row["low"]) - 1
            high_idx = np.searchsorted(bins, row["high"])
            low_idx = max(0, low_idx)
            high_idx = min(num_bins - 1, high_idx)

            n_bins_in_bar = max(1, high_idx - low_idx + 1)
            per_bin = vol // n_bins_in_bar
            remainder = vol % n_bins_in_bar

            for i in range(low_idx, high_idx + 1):
                bin_volumes[i] += per_bin + (1 if i - low_idx < remainder else 0)

        # Price for each bin (midpoint)
        bin_prices = (bins[:-1] + bins[1:]) / 2

        # POC = max volume bin
        poc_idx = int(np.argmax(bin_volumes))
        poc = round(float(bin_prices[poc_idx]), 2)

        # Value Area (70% of total volume centered on POC)
        total_vol = bin_volumes.sum()
        target_vol = total_vol * va_pct

        upper_idx = poc_idx
        lower_idx = poc_idx
        area_vol = bin_volumes[poc_idx]

        while area_vol < target_vol:
            can_up = upper_idx + 1 < num_bins
            can_down = lower_idx - 1 >= 0

            if not can_up and not can_down:
                break

            vol_above = bin_volumes[upper_idx + 1] if can_up else 0
            vol_below = bin_volumes[lower_idx - 1] if can_down else 0

            if vol_above >= vol_below and can_up:
                upper_idx += 1
                area_vol += bin_volumes[upper_idx]
            elif can_down:
                lower_idx -= 1
                area_vol += bin_volumes[lower_idx]
            else:
                break

        vah = round(float(bin_prices[upper_idx]), 2)
        val = round(float(bin_prices[lower_idx]), 2)

        # HVN and LVN
        avg_vol = bin_volumes.mean()
        hvn = [round(float(bin_prices[i]), 2) for i in range(num_bins)
               if bin_volumes[i] >= avg_vol * hvn_threshold]
        lvn = [round(float(bin_prices[i]), 2) for i in range(num_bins)
               if bin_volumes[i] > 0 and bin_volumes[i] <= avg_vol * lvn_threshold]

        # Single prints (zero volume = truly empty = very fast zone)
        single_prints = [round(float(bin_prices[i]), 2) for i in range(num_bins)
                         if bin_volumes[i] == 0]

        # Profile bias: is majority of volume above or below POC?
        vol_above_poc = bin_volumes[poc_idx:].sum()
        vol_below_poc = bin_volumes[:poc_idx].sum()
        is_bullish_profile = vol_above_poc <= vol_below_poc  # volume above = resistance; more below = bullish

        distribution = pd.DataFrame({
            "price": bin_prices,
            "volume": bin_volumes,
            "pct": bin_volumes / total_vol if total_vol > 0 else 0,
        })

        return VolumeProfileResult(
            poc=poc,
            vah=vah,
            val=val,
            value_area_pct=va_pct,
            hvn=hvn[:10],
            lvn=lvn[:10],
            single_prints=single_prints[:20],
            total_volume=int(total_vol),
            is_bullish_profile=is_bullish_profile,
            distribution=distribution,
        )

    def nearest_hvn(self, profile: VolumeProfileResult, price: float) -> float | None:
        if not profile.hvn:
            return None
        return min(profile.hvn, key=lambda x: abs(x - price))

    def nearest_lvn(self, profile: VolumeProfileResult, price: float) -> float | None:
        if not profile.lvn:
            return None
        return min(profile.lvn, key=lambda x: abs(x - price))

    def price_at_poc(self, profile: VolumeProfileResult, price: float, tolerance_pct: float = 0.002) -> bool:
        return abs(price - profile.poc) / profile.poc <= tolerance_pct if profile.poc > 0 else False

    def price_in_value_area(self, profile: VolumeProfileResult, price: float) -> bool:
        return profile.val <= price <= profile.vah

    def price_outside_value_area(self, profile: VolumeProfileResult, price: float) -> str:
        if price > profile.vah:
            return "ABOVE_VA"
        elif price < profile.val:
            return "BELOW_VA"
        return "INSIDE_VA"


volume_profile_engine = VolumeProfileEngine()

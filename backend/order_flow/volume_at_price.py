"""
Volume At Price (VAP) / Market Profile data structure.
Groups all traded volume by price level.
Foundation for Volume Profile Agent (POC, VAH, VAL, HVN, LVN).
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class VAPBar:
    price: float
    total_vol: int
    buy_vol: int
    sell_vol: int
    delta: int        # buy - sell at this price


class VolumeAtPrice:
    """
    Maintains a running volume-at-price distribution.
    Can be built from historical OHLCV or live tick data.
    """

    def __init__(self, tick_size: float = 0.05):
        self.tick_size = tick_size
        self._distribution: defaultdict = defaultdict(lambda: {"total": 0, "buy": 0, "sell": 0})

    def _bucket(self, price: float) -> float:
        """Round price to nearest tick."""
        return round(round(price / self.tick_size) * self.tick_size, 2)

    def add_tick(self, price: float, volume: int, direction: str):
        """Add a single classified tick."""
        bucket = self._bucket(price)
        self._distribution[bucket]["total"] += volume
        if direction == "BUY":
            self._distribution[bucket]["buy"] += volume
        else:
            self._distribution[bucket]["sell"] += volume

    def add_ohlcv_bar(self, o: float, h: float, l: float, c: float, v: int):
        """
        Distribute bar volume uniformly across its high-low range.
        Used when tick data is unavailable (historical OHLCV).
        """
        prices = np.arange(self._bucket(l), self._bucket(h) + self.tick_size, self.tick_size)
        if len(prices) == 0:
            self.add_tick(c, v, "BUY")
            return
        vol_per_tick = v // len(prices)
        remainder = v % len(prices)
        for i, price in enumerate(prices):
            vol = vol_per_tick + (1 if i < remainder else 0)
            direction = "BUY" if c >= (h + l) / 2 else "SELL"
            self.add_tick(price, vol, direction)

    def build_from_df(self, df: pd.DataFrame):
        """Build full VAP from OHLCV DataFrame."""
        self._distribution.clear()
        for _, row in df.iterrows():
            self.add_ohlcv_bar(
                row["open"], row["high"], row["low"], row["close"], int(row["volume"])
            )

    def get_bars(self) -> list[VAPBar]:
        bars = []
        for price, data in sorted(self._distribution.items()):
            bars.append(VAPBar(
                price=price,
                total_vol=data["total"],
                buy_vol=data["buy"],
                sell_vol=data["sell"],
                delta=data["buy"] - data["sell"],
            ))
        return bars

    def get_distribution_df(self) -> pd.DataFrame:
        bars = self.get_bars()
        if not bars:
            return pd.DataFrame()
        return pd.DataFrame([{
            "price": b.price, "total_vol": b.total_vol,
            "buy_vol": b.buy_vol, "sell_vol": b.sell_vol, "delta": b.delta
        } for b in bars])

    def clear(self):
        self._distribution.clear()


# Per-symbol VAP instances
_vap_instances: dict[str, VolumeAtPrice] = {}


def get_vap(symbol: str, tick_size: float = 0.05) -> VolumeAtPrice:
    if symbol not in _vap_instances:
        _vap_instances[symbol] = VolumeAtPrice(tick_size)
    return _vap_instances[symbol]

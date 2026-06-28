"""
Tick Aggregator — classifies each tick as buyer-initiated or seller-initiated.
Uses the Lee-Ready algorithm: uptick = buy, downtick = sell, zero-tick = direction of last non-zero tick.
"""

import asyncio
import json
from collections import deque
from datetime import datetime
from loguru import logger
from backend.redis_client import redis_client


class TickAggregator:
    """
    Processes raw ticks from KiteWebSocket and classifies each as:
    - BUY (aggressor = buyer, price >= last ask / uptick)
    - SELL (aggressor = seller, price <= last bid / downtick)
    Then aggregates into 1-minute footprint bars.
    """

    def __init__(self, symbol: str, max_history: int = 1000):
        self.symbol = symbol
        self.max_history = max_history
        self._ticks: deque = deque(maxlen=max_history)
        self._last_price: float | None = None
        self._last_direction: str = "BUY"    # Lee-Ready zero-tick rule
        self._current_bar = self._new_bar()

    def _new_bar(self, timestamp: str = None) -> dict:
        return {
            "ts": timestamp or datetime.now().strftime("%H:%M"),
            "open": 0.0, "high": 0.0, "low": float("inf"), "close": 0.0,
            "volume": 0,
            "buy_vol": 0,    # aggressor buyer volume
            "sell_vol": 0,   # aggressor seller volume
            "buy_count": 0,
            "sell_count": 0,
            "delta": 0,      # buy_vol - sell_vol
        }

    def _classify_tick(self, price: float, bid: float = None, ask: float = None) -> str:
        """Lee-Ready classification."""
        if self._last_price is None:
            self._last_price = price
            return "BUY"

        if price > self._last_price:
            direction = "BUY"
        elif price < self._last_price:
            direction = "SELL"
        else:
            direction = self._last_direction   # zero-tick rule

        self._last_price = price
        self._last_direction = direction
        return direction

    def process_tick(self, tick: dict) -> dict | None:
        """
        Process a single tick. Returns the completed bar when a new minute starts.
        """
        ltp = tick.get("last_price", 0)
        vol = tick.get("last_quantity", tick.get("volume_traded", 1))
        ts = datetime.now()
        bar_ts = ts.strftime("%H:%M")

        depth = tick.get("depth", {})
        best_bid = depth.get("buy", [{}])[0].get("price", ltp) if depth.get("buy") else ltp
        best_ask = depth.get("sell", [{}])[0].get("price", ltp) if depth.get("sell") else ltp

        direction = self._classify_tick(ltp, best_bid, best_ask)

        classified = {
            "ts": ts.isoformat(),
            "price": ltp,
            "volume": vol,
            "direction": direction,
            "bid": best_bid,
            "ask": best_ask,
        }
        self._ticks.append(classified)

        # Aggregate into current bar
        if self._current_bar["ts"] != bar_ts:
            completed = self._current_bar.copy()
            self._current_bar = self._new_bar(bar_ts)
            self._update_bar(ltp, vol, direction)
            return completed if completed["volume"] > 0 else None

        self._update_bar(ltp, vol, direction)
        return None

    def _update_bar(self, price: float, volume: int, direction: str):
        bar = self._current_bar
        if bar["open"] == 0.0:
            bar["open"] = price
        bar["high"] = max(bar["high"], price)
        bar["low"] = min(bar["low"], price)
        bar["close"] = price
        bar["volume"] += volume

        if direction == "BUY":
            bar["buy_vol"] += volume
            bar["buy_count"] += 1
        else:
            bar["sell_vol"] += volume
            bar["sell_count"] += 1
        bar["delta"] = bar["buy_vol"] - bar["sell_vol"]

    def get_recent_ticks(self, n: int = 100) -> list[dict]:
        return list(self._ticks)[-n:]

    def get_current_bar(self) -> dict:
        return self._current_bar.copy()


# Registry of per-symbol aggregators
_aggregators: dict[str, TickAggregator] = {}


def get_aggregator(symbol: str) -> TickAggregator:
    if symbol not in _aggregators:
        _aggregators[symbol] = TickAggregator(symbol)
    return _aggregators[symbol]

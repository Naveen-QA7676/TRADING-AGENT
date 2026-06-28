"""
Kite Connect WebSocket — real-time tick data streaming.
Publishes to Redis so all consumers (agents, position monitor, order flow) stay live.
"""

import asyncio
import json
import threading
from datetime import datetime
from typing import Callable
from loguru import logger

from kiteconnect import KiteTicker
from backend.config import settings
from backend.redis_client import redis_client
from backend.broker.kite_auth import kite_session


class KiteWebSocketManager:
    """Manages the KiteTicker WebSocket with auto-reconnect."""

    def __init__(self):
        self._ticker: KiteTicker | None = None
        self._subscribed_tokens: set[int] = set()
        self._tick_callbacks: list[Callable] = []
        self._running = False
        self._thread: threading.Thread | None = None

        # In-memory latest ticks cache
        self._latest_ticks: dict[int, dict] = {}

    def add_tick_callback(self, fn: Callable):
        self._tick_callbacks.append(fn)

    def start(self, access_token: str, tokens: list[int]):
        """Start WebSocket in a background thread."""
        if self._running:
            return

        self._ticker = KiteTicker(settings.kite_api_key, access_token)

        self._ticker.on_connect = self._on_connect
        self._ticker.on_ticks = self._on_ticks
        self._ticker.on_close = self._on_close
        self._ticker.on_error = self._on_error
        self._ticker.on_reconnect = self._on_reconnect
        self._ticker.on_noreconnect = self._on_noreconnect

        self._subscribed_tokens = set(tokens)
        self._running = True

        self._thread = threading.Thread(
            target=self._ticker.connect, kwargs={"threaded": True}, daemon=True
        )
        self._thread.start()
        logger.info(f"KiteWebSocket started. Subscribed to {len(tokens)} instruments.")

    def subscribe(self, tokens: list[int]):
        new = set(tokens) - self._subscribed_tokens
        if new and self._ticker:
            self._ticker.subscribe(list(new))
            self._ticker.set_mode(self._ticker.MODE_FULL, list(new))
            self._subscribed_tokens.update(new)
            logger.debug(f"WebSocket: subscribed to {new}")

    def unsubscribe(self, tokens: list[int]):
        if self._ticker:
            self._ticker.unsubscribe(tokens)
            self._subscribed_tokens -= set(tokens)

    def stop(self):
        self._running = False
        if self._ticker:
            self._ticker.stop()
        logger.info("KiteWebSocket stopped.")

    def get_latest_tick(self, token: int) -> dict | None:
        return self._latest_ticks.get(token)

    # ── Private callbacks ──────────────────────────────────────────────────

    def _on_connect(self, ws, response):
        logger.success("KiteWebSocket connected.")
        if self._subscribed_tokens:
            tokens = list(self._subscribed_tokens)
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)

    def _on_ticks(self, ws, ticks: list[dict]):
        for tick in ticks:
            token = tick.get("instrument_token")
            self._latest_ticks[token] = tick

            # Publish to Redis for other consumers
            tick_json = json.dumps({
                "token": token,
                "symbol": tick.get("tradingsymbol", ""),
                "ltp": tick.get("last_price", 0),
                "volume": tick.get("volume", 0),
                "ohlc": tick.get("ohlc", {}),
                "depth": tick.get("depth", {}),
                "change": tick.get("change", 0),
                "avg_price": tick.get("average_price", 0),
                "buy_qty": tick.get("buy_quantity", 0),
                "sell_qty": tick.get("sell_quantity", 0),
                "timestamp": datetime.now().isoformat(),
            })
            asyncio.run_coroutine_threadsafe(
                redis_client.publish(f"tick:{token}", tick_json),
                asyncio.get_event_loop(),
            )

            # Fire any registered callbacks
            for cb in self._tick_callbacks:
                try:
                    cb(tick)
                except Exception as e:
                    logger.error(f"Tick callback error: {e}")

    def _on_close(self, ws, code, reason):
        logger.warning(f"KiteWebSocket closed: {code} — {reason}")

    def _on_error(self, ws, code, reason):
        logger.error(f"KiteWebSocket error: {code} — {reason}")

    def _on_reconnect(self, ws, attempts):
        logger.info(f"KiteWebSocket reconnecting... attempt {attempts}")

    def _on_noreconnect(self, ws):
        logger.critical("KiteWebSocket failed to reconnect. Manual intervention required.")
        self._running = False


ws_manager = KiteWebSocketManager()

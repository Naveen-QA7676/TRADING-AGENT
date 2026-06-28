"""
Live position monitoring — tracks unrealized P&L, MAE/MFE, SL/target proximity,
and publishes real-time updates to Redis for the dashboard.
"""

import asyncio
import json
from datetime import datetime
from loguru import logger

from backend.broker.kite_auth import kite_session
from backend.broker.kite_websocket import ws_manager
from backend.redis_client import redis_client, CHANNELS
from backend.config import settings


class PositionMonitor:

    def __init__(self):
        self._positions: dict[str, dict] = {}   # symbol → position data
        self._running = False

    async def start(self):
        self._running = True
        logger.info("Position monitor started.")
        while self._running:
            try:
                await self._sync_positions()
                await self._check_risk_limits()
                await self._publish_updates()
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
            await asyncio.sleep(2)   # update every 2 seconds

    def stop(self):
        self._running = False

    async def _sync_positions(self):
        try:
            positions = kite_session.get_positions()
            day_pos = positions.get("day", [])
            current_symbols = set()

            for pos in day_pos:
                if pos["product"] != "MIS" or pos["quantity"] == 0:
                    continue
                symbol = pos["tradingsymbol"]
                current_symbols.add(symbol)

                # Get latest tick for current price
                ltp = pos.get("last_price", pos.get("average_price", 0))
                tick = ws_manager.get_latest_tick(pos.get("instrument_token", 0))
                if tick:
                    ltp = tick.get("last_price", ltp)

                qty = pos["quantity"]
                avg = pos["average_price"]
                pnl = (ltp - avg) * qty if qty > 0 else (avg - ltp) * abs(qty)
                pnl_pct = ((ltp - avg) / avg) * 100 if avg > 0 else 0

                existing = self._positions.get(symbol, {})
                mae = existing.get("max_adverse_excursion", 0)
                mfe = existing.get("max_favorable_excursion", 0)
                if pnl < mae:
                    mae = pnl
                if pnl > mfe:
                    mfe = pnl

                self._positions[symbol] = {
                    "symbol": symbol,
                    "exchange": pos["exchange"],
                    "quantity": qty,
                    "direction": "LONG" if qty > 0 else "SHORT",
                    "entry_price": avg,
                    "current_price": ltp,
                    "unrealized_pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "max_adverse_excursion": round(mae, 2),
                    "max_favorable_excursion": round(mfe, 2),
                    "last_updated": datetime.now().isoformat(),
                }

            # Remove closed positions
            for sym in list(self._positions.keys()):
                if sym not in current_symbols:
                    del self._positions[sym]

        except Exception as e:
            logger.error(f"Position sync error: {e}")

    async def _check_risk_limits(self):
        """Auto square-off if daily loss limit hit."""
        total_unrealized = sum(p["unrealized_pnl"] for p in self._positions.values())
        today_key = f"daily:realized_pnl:{datetime.now().strftime('%Y-%m-%d')}"
        realized = float(await redis_client.get(today_key) or 0)
        total_pnl = realized + total_unrealized
        loss_limit = -settings.daily_loss_limit

        if total_pnl <= loss_limit:
            logger.critical(
                f"DAILY LOSS LIMIT HIT! P&L={total_pnl:.0f} limit={loss_limit:.0f}. "
                "Auto square-off triggered."
            )
            from backend.broker.orders import order_manager
            order_manager.squareoff_all_positions()
            await redis_client.set("trading:disabled_today", "1", ex=86400)

    async def _publish_updates(self):
        if not self._positions:
            return
        payload = json.dumps({"positions": list(self._positions.values()), "ts": datetime.now().isoformat()})
        await redis_client.publish(CHANNELS["position_update"], payload)

    def get_all_positions(self) -> list[dict]:
        return list(self._positions.values())

    def get_position(self, symbol: str) -> dict | None:
        return self._positions.get(symbol)

    def get_open_count(self) -> int:
        return len(self._positions)


position_monitor = PositionMonitor()

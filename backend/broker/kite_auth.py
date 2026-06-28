"""
Zerodha Kite Connect authentication with daily token management.
Login URL generation → OAuth callback → access token → stored in Redis.
"""

import asyncio
from datetime import datetime
from loguru import logger

from kiteconnect import KiteConnect
from backend.config import settings
from backend.redis_client import redis_client, KEYS


class KiteSession:
    """Singleton that holds the authenticated KiteConnect instance."""

    def __init__(self):
        self._kite: KiteConnect | None = None
        self._access_token: str | None = None
        self._connected: bool = False

    def is_connected(self) -> bool:
        return self._connected and self._kite is not None

    @property
    def kite(self) -> KiteConnect:
        if not self._kite:
            raise RuntimeError("Kite session not initialised. Complete OAuth login first.")
        return self._kite

    def get_login_url(self) -> str:
        """Step 1: generate the Zerodha OAuth URL for the user to open."""
        kite = KiteConnect(api_key=settings.kite_api_key)
        url = kite.login_url()
        logger.info(f"Kite login URL generated: {url}")
        return url

    async def complete_login(self, request_token: str) -> str:
        """
        Step 2: exchange request_token for access_token.
        Called from the OAuth callback route.
        """
        kite = KiteConnect(api_key=settings.kite_api_key)
        data = kite.generate_session(request_token, api_secret=settings.kite_secret)
        access_token = data["access_token"]

        kite.set_access_token(access_token)
        self._kite = kite
        self._access_token = access_token
        self._connected = True

        # Persist to Redis (expires at 3:30 AM next day — Kite tokens expire daily)
        await redis_client.set(KEYS["kite_token"], access_token, ex=86400)
        logger.success(f"Kite login complete for user {data.get('user_id')}")
        return access_token

    async def restore_from_redis(self) -> bool:
        """On startup: try to restore a token saved earlier today."""
        token = await redis_client.get(KEYS["kite_token"])
        if not token:
            logger.warning("No cached Kite token found. Manual login required.")
            return False
        try:
            kite = KiteConnect(api_key=settings.kite_api_key)
            kite.set_access_token(token)
            # Verify with a quick profile call
            profile = kite.profile()
            self._kite = kite
            self._access_token = token
            self._connected = True
            logger.success(f"Kite session restored for {profile.get('user_name')}")
            return True
        except Exception as e:
            logger.error(f"Cached token invalid: {e}")
            await redis_client.delete(KEYS["kite_token"])
            return False

    async def logout(self):
        if self._kite:
            try:
                self._kite.invalidate_session()
            except Exception:
                pass
        self._kite = None
        self._access_token = None
        self._connected = False
        await redis_client.delete(KEYS["kite_token"])
        logger.info("Kite session logged out.")

    def get_instruments(self, exchange: str = "NSE") -> list:
        return self.kite.instruments(exchange)

    def get_profile(self) -> dict:
        return self.kite.profile()

    def get_margins(self) -> dict:
        return self.kite.margins()

    def get_holdings(self) -> list:
        return self.kite.holdings()

    def get_positions(self) -> dict:
        return self.kite.positions()

    def get_orders(self) -> list:
        return self.kite.orders()

    def get_quote(self, symbols: list[str]) -> dict:
        """e.g. symbols = ["NSE:HDFCBANK", "NSE:RELIANCE"]"""
        return self.kite.quote(symbols)

    def get_ltp(self, symbols: list[str]) -> dict:
        return self.kite.ltp(symbols)

    def get_historical_data(
        self,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str,
        continuous: bool = False,
    ) -> list[dict]:
        """
        interval: "minute", "3minute", "5minute", "15minute", "30minute",
                  "60minute", "day"
        """
        return self.kite.historical_data(
            instrument_token, from_date, to_date, interval, continuous
        )

    def get_ohlc(self, symbols: list[str]) -> dict:
        return self.kite.ohlc(symbols)

    def get_market_depth(self, symbols: list[str]) -> dict:
        return self.kite.quote(symbols)


kite_session = KiteSession()

"""
Kite Connect OAuth flow + system status.

Flow:
  1. GET  /api/auth/login-url       → returns the Zerodha login URL
  2. GET  /api/auth/callback?request_token=xxx  → exchanges token, stores session
  3. GET  /api/auth/status          → is Kite connected?
  4. POST /api/auth/logout          → invalidates session
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from loguru import logger

from backend.broker.kite_auth import kite_session
from backend.redis_client import redis_client

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login-url")
async def get_login_url():
    """
    Step 1: Generate the Zerodha OAuth URL.
    User opens this URL in browser → logs in → redirected back with ?request_token=
    """
    try:
        url = kite_session.get_login_url()
        return {"login_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate login URL: {e}")


@router.get("/callback")
async def kite_callback(request_token: str):
    """
    Step 2: Zerodha redirects here after login.
    Exchange the request_token for an access_token and start the platform.
    """
    try:
        access_token = await kite_session.complete_login(request_token)
        logger.success(f"Kite login complete. Token stored.")

        # Start WebSocket tick streaming
        try:
            from backend.broker.kite_websocket import ws_manager
            from backend.agents.execution_intelligence.scanner_agent import NIFTY_500_SYMBOLS

            # Get instrument tokens for watchlist
            instruments = kite_session.get_instruments("NSE")
            nse_tokens = {
                inst["tradingsymbol"]: inst["instrument_token"]
                for inst in instruments
                if inst["segment"] == "NSE" and inst["tradingsymbol"] in NIFTY_500_SYMBOLS
            }
            tokens = list(nse_tokens.values())[:100]  # subscribe to top 100

            if tokens:
                ws_manager.start(access_token, tokens)
                logger.info(f"WebSocket started for {len(tokens)} instruments")
        except Exception as e:
            logger.warning(f"WebSocket start failed (non-fatal): {e}")

        return {
            "status": "connected",
            "message": "Kite session established. Platform is ready.",
        }
    except Exception as e:
        logger.error(f"Kite callback error: {e}")
        raise HTTPException(status_code=400, detail=f"Login failed: {e}")


@router.get("/status")
async def auth_status():
    """Check if Kite session is active and platform is operational."""
    connected = kite_session.is_connected()
    profile = {}
    if connected:
        try:
            profile = kite_session.get_profile()
        except Exception:
            pass

    trading_disabled = bool(await redis_client.get("trading:disabled_today"))

    return {
        "kite_connected":    connected,
        "user_name":         profile.get("user_name", ""),
        "user_id":           profile.get("user_id", ""),
        "trading_disabled":  trading_disabled,
        "message": (
            "Kite connected and platform is running." if connected
            else "Kite not connected. Visit /api/auth/login-url to authenticate."
        ),
    }


@router.post("/logout")
async def logout():
    """Invalidate the Kite session and stop trading."""
    try:
        from backend.broker.kite_websocket import ws_manager
        ws_manager.stop()
    except Exception:
        pass
    await kite_session.logout()
    return {"status": "logged_out", "message": "Kite session terminated."}


@router.post("/reset-daily-limits")
async def reset_daily_limits():
    """Re-enable trading if it was disabled by the daily loss limit (use with care)."""
    await redis_client.delete("trading:disabled_today")
    return {"status": "reset", "message": "Daily trading limit reset. Trading re-enabled."}

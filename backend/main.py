"""
AI Institutional Trading Intelligence Platform — FastAPI entry point.
"""

import asyncio
from contextlib import asynccontextmanager
from loguru import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.config import settings
from backend.database import engine, Base
from backend.redis_client import redis_client
from backend.scheduler import start_scheduler, shutdown_scheduler

from backend.routers import (
    suggestions, positions, news, journal,
    stocks, tax, terminal, scanner, agents_status, backtest, auth
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Trading Intelligence Platform...")

    # Create all DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")

    # Verify Redis
    await redis_client.ping()
    logger.info("Redis connected.")

    # Restore Kite session from Redis (persisted across restarts)
    from backend.broker.kite_auth import kite_session
    try:
        restored = await kite_session.restore_from_redis()
        if restored:
            logger.success("Kite session restored from Redis cache.")
            # Resume position monitoring
            try:
                from backend.broker.position_monitor import position_monitor
                asyncio.create_task(position_monitor.start())
                logger.info("Position monitor started.")
            except Exception as e:
                logger.warning(f"Position monitor start failed: {e}")
        else:
            logger.info("No cached Kite session — authenticate via GET /api/auth/login-url")
    except Exception as e:
        logger.warning(f"Kite session restore failed (non-fatal): {e}")

    # Start the scheduler (daily research, market scans, square-off)
    start_scheduler()
    logger.info("Scheduler started.")

    yield  # App is running

    # Shutdown
    logger.info("Shutting down...")
    shutdown_scheduler()

    # Stop WebSocket if running
    try:
        from backend.broker.kite_websocket import ws_manager
        ws_manager.stop()
    except Exception:
        pass

    await redis_client.aclose()
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="AI Institutional Trading Intelligence Platform",
    description="21-agent autonomous trading intelligence system for Zerodha",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(suggestions.router, prefix="/api/suggestions", tags=["Suggestions"])
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(journal.router, prefix="/api/journal", tags=["Journal"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["Stocks"])
app.include_router(tax.router, prefix="/api/tax", tags=["Tax"])
app.include_router(terminal.router, prefix="/api/terminal", tags=["Terminal"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["Scanner"])
app.include_router(agents_status.router, prefix="/api/agents", tags=["Agents"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/status")
async def system_status():
    from backend.redis_client import redis_client
    from backend.broker.kite_auth import kite_session

    return {
        "platform": "AI Institutional Trading Intelligence Platform",
        "version": "1.0.0",
        "broker_connected": kite_session.is_connected(),
        "redis_ok": await redis_client.ping(),
        "trading_capital": settings.capital,
        "max_risk_per_trade_pct": settings.max_risk_per_trade * 100,
    }

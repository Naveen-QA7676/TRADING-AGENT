import redis.asyncio as aioredis
from backend.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    max_connections=20,
)

# Channel names for Pub/Sub
CHANNELS = {
    "new_suggestion": "channel:suggestions:new",
    "position_update": "channel:positions:update",
    "breaking_news": "channel:news:breaking",
    "agent_status": "channel:agents:status",
    "trade_executed": "channel:trades:executed",
    "squareoff_alert": "channel:squareoff:alert",
    "regime_change": "channel:regime:change",
}

# Redis key patterns
KEYS = {
    "kite_token": "kite:access_token",
    "market_regime": "market:regime",
    "daily_pnl": "daily:pnl:{date}",
    "open_positions_count": "positions:open:count",
    "agent_status": "agents:status:{agent_name}",
    "last_scan": "scanner:last_scan",
    "suggestion": "suggestion:{id}",
}

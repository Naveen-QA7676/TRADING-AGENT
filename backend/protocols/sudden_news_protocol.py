"""
Sudden News Protocol — triggered when HIGH/BREAKING impact news arrives during market hours.
Actions: re-evaluate open positions, cancel pending suggestions, adjust risk.
"""

import json
import asyncio
from loguru import logger
from backend.redis_client import redis_client, CHANNELS


class SuddenNewsProtocol:
    """
    When breaking news hits:
    1. Immediately cancel all pending YES/NO suggestion timers
    2. Evaluate each open position against the news
    3. If news is VERY NEGATIVE → force square-off of exposed positions
    4. Notify user via dashboard with red banner
    5. Disable new suggestions until news is assessed
    """

    async def trigger(self, news_item: dict, open_positions: list[dict]) -> dict:
        """
        Process a breaking news event.
        Returns dict with actions taken.
        """
        headline = news_item.get("headline", "")
        sentiment = news_item.get("sentiment", "NEUTRAL")
        impact = news_item.get("impact", "MEDIUM")
        affected_symbols = news_item.get("affected_symbols", [])

        actions = {
            "news_id": news_item.get("id"),
            "headline": headline,
            "impact": impact,
            "sentiment": sentiment,
            "positions_evaluated": [],
            "suggestions_cancelled": False,
            "squareoffs_triggered": [],
            "alert_sent": False,
        }

        logger.warning(f"SUDDEN NEWS PROTOCOL TRIGGERED: {headline}")

        # Step 1: Cancel pending suggestions
        if impact in ["HIGH", "BREAKING"]:
            await redis_client.set("suggestions:paused", "1", ex=300)  # pause 5 min
            actions["suggestions_cancelled"] = True
            logger.warning("Trade suggestions PAUSED for 5 minutes due to breaking news")

        # Step 2: Evaluate each open position
        for pos in open_positions:
            sym = pos.get("symbol", "")
            pnl = pos.get("unrealized_pnl", 0)

            if sym in affected_symbols or "ALL" in affected_symbols:
                position_action = await self._evaluate_position(pos, news_item)
                actions["positions_evaluated"].append({
                    "symbol": sym,
                    "action": position_action,
                })

                if position_action == "FORCE_EXIT":
                    actions["squareoffs_triggered"].append(sym)
                    logger.warning(f"FORCE EXIT: {sym} due to breaking news impact")
                    from backend.broker.orders import order_manager
                    try:
                        order_manager.place_market_order(
                            symbol=sym,
                            transaction_type="SELL" if pos.get("direction") == "LONG" else "BUY",
                            quantity=abs(pos.get("quantity", 0)),
                        )
                    except Exception as e:
                        logger.error(f"Force exit failed for {sym}: {e}")

        # Step 3: Publish alert to dashboard
        alert_payload = json.dumps({
            "type": "BREAKING_NEWS",
            "headline": headline,
            "sentiment": sentiment,
            "impact": impact,
            "affected_symbols": affected_symbols,
            "actions": actions,
            "timestamp": str(asyncio.get_event_loop().time()),
        })
        await redis_client.publish(CHANNELS["breaking_news"], alert_payload)
        actions["alert_sent"] = True

        return actions

    async def _evaluate_position(self, position: dict, news_item: dict) -> str:
        """
        Decide what to do with an open position given the news.
        Returns: "HOLD", "REDUCE", "FORCE_EXIT"
        """
        sentiment = news_item.get("sentiment", "NEUTRAL")
        impact = news_item.get("impact", "LOW")
        pnl = position.get("unrealized_pnl", 0)
        direction = position.get("direction", "LONG")

        # Very bearish news + long position → force exit
        if sentiment == "BEARISH" and impact == "BREAKING" and direction == "LONG":
            return "FORCE_EXIT"

        # High impact + position is losing → force exit to protect capital
        if impact == "HIGH" and sentiment == "BEARISH" and pnl < 0 and direction == "LONG":
            return "FORCE_EXIT"

        # Medium impact → HOLD but move SL to entry
        if impact == "MEDIUM" and sentiment == "BEARISH":
            return "REDUCE"

        return "HOLD"


sudden_news_protocol = SuddenNewsProtocol()

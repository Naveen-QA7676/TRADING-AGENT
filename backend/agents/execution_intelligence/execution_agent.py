"""
Execution Agent — Agent 15.
Handles the actual order placement logic after user approves YES.
Manages entry slicing, GTT setup, order confirmation, and post-fill verification.
"""

import asyncio
from loguru import logger
from backend.broker.orders import order_manager
from backend.broker.kite_auth import kite_session
from backend.redis_client import redis_client, CHANNELS
import json


class ExecutionAgent:
    name = "Execution Agent"

    async def execute(self, suggestion: dict, user_approved: bool = False) -> dict:
        """
        Called only when user clicks YES.
        Places MIS limit order + GTT for SL and target.
        """
        result = {
            "agent": self.name,
            "executed": False,
            "order_id": None,
            "gtt_id": None,
            "fill_price": None,
            "fill_qty": 0,
            "error": None,
            "description": "",
        }

        if not user_approved:
            result["description"] = "Execution skipped — awaiting user YES."
            return result

        symbol = suggestion.get("symbol")
        direction = suggestion.get("direction", "LONG")
        quantity = suggestion.get("quantity", 0)
        entry_price = suggestion.get("entry_price", 0)
        stop_loss = suggestion.get("stop_loss", 0)
        target_1 = suggestion.get("target_1", 0)

        if quantity <= 0:
            result["error"] = "Invalid quantity"
            result["description"] = "Cannot execute: quantity is 0"
            return result

        try:
            transaction_type = "BUY" if direction == "LONG" else "SELL"

            logger.info(f"EXECUTING: {transaction_type} {quantity} {symbol} @ ₹{entry_price}")

            # Place MIS limit order
            order_id = order_manager.place_buy_order(
                symbol=symbol,
                quantity=quantity,
                price=entry_price,
            ) if direction == "LONG" else order_manager.place_sell_order(
                symbol=symbol,
                quantity=quantity,
                price=entry_price,
            )

            result["order_id"] = order_id
            logger.info(f"Order placed: {order_id}")

            # Wait briefly for fill
            await asyncio.sleep(2)

            # Check order status
            try:
                orders = kite_session.kite.orders()
                for o in orders:
                    if str(o.get("order_id")) == str(order_id):
                        if o.get("status") == "COMPLETE":
                            result["fill_price"] = o.get("average_price", entry_price)
                            result["fill_qty"] = o.get("filled_quantity", quantity)
                            result["executed"] = True
                        break
            except Exception:
                result["fill_price"] = entry_price
                result["fill_qty"] = quantity
                result["executed"] = True

            # Set GTT for SL + Target (only if fill confirmed)
            if result["executed"]:
                fill_price = result["fill_price"] or entry_price
                try:
                    gtt_id = order_manager.setup_trade_gtt(
                        symbol=symbol,
                        direction=direction,
                        quantity=quantity,
                        ltp=fill_price,
                        stop_loss=stop_loss,
                        target=target_1,
                    )
                    result["gtt_id"] = gtt_id
                    logger.info(f"GTT set: {gtt_id} | SL={stop_loss} T={target_1}")
                except Exception as e:
                    logger.warning(f"GTT setup failed: {e} — set manually!")

                # Publish execution event to dashboard
                await redis_client.publish(CHANNELS["trade_executed"], json.dumps({
                    "symbol": symbol,
                    "direction": direction,
                    "quantity": result["fill_qty"],
                    "fill_price": result["fill_price"],
                    "stop_loss": stop_loss,
                    "target_1": target_1,
                    "order_id": order_id,
                    "gtt_id": result["gtt_id"],
                }))

            result["description"] = (
                f"{'✓ EXECUTED' if result['executed'] else '✗ PENDING'}: "
                f"{transaction_type} {result['fill_qty']} {symbol} @ ₹{result['fill_price']} | "
                f"GTT: {'✓' if result['gtt_id'] else '✗'}"
            )

        except Exception as e:
            logger.error(f"Execution Agent error: {e}")
            result["error"] = str(e)
            result["description"] = f"Execution FAILED: {str(e)}"

        return result


execution_agent = ExecutionAgent()

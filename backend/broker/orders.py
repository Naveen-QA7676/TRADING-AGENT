"""
Order placement, modification, and cancellation via Kite Connect.
All intraday orders use MIS product type.
"""

from datetime import datetime
from loguru import logger
from kiteconnect import KiteConnect

from backend.broker.kite_auth import kite_session
from backend.config import settings


class OrderManager:

    @staticmethod
    def place_buy_order(
        symbol: str,
        quantity: int,
        order_type: str = "LIMIT",
        price: float = 0.0,
        trigger_price: float = 0.0,
        exchange: str = "NSE",
    ) -> str:
        """Place an intraday MIS BUY order. Returns order_id."""
        kite = kite_session.kite
        params = {
            "tradingsymbol": symbol,
            "exchange": exchange,
            "transaction_type": kite.TRANSACTION_TYPE_BUY,
            "quantity": quantity,
            "product": kite.PRODUCT_MIS,
            "order_type": kite.ORDER_TYPE_LIMIT if order_type == "LIMIT" else kite.ORDER_TYPE_MARKET,
            "price": price if order_type == "LIMIT" else 0,
            "validity": kite.VALIDITY_DAY,
        }
        if trigger_price:
            params["trigger_price"] = trigger_price
            params["order_type"] = kite.ORDER_TYPE_SL

        order_id = kite.place_order(variety=kite.VARIETY_REGULAR, **params)
        logger.info(f"BUY order placed: {symbol} × {quantity} @ {price} → Order ID: {order_id}")
        return order_id

    @staticmethod
    def place_sell_order(
        symbol: str,
        quantity: int,
        order_type: str = "LIMIT",
        price: float = 0.0,
        trigger_price: float = 0.0,
        exchange: str = "NSE",
    ) -> str:
        kite = kite_session.kite
        params = {
            "tradingsymbol": symbol,
            "exchange": exchange,
            "transaction_type": kite.TRANSACTION_TYPE_SELL,
            "quantity": quantity,
            "product": kite.PRODUCT_MIS,
            "order_type": kite.ORDER_TYPE_LIMIT if order_type == "LIMIT" else kite.ORDER_TYPE_MARKET,
            "price": price if order_type == "LIMIT" else 0,
            "validity": kite.VALIDITY_DAY,
        }
        if trigger_price:
            params["trigger_price"] = trigger_price
            params["order_type"] = kite.ORDER_TYPE_SL

        order_id = kite.place_order(variety=kite.VARIETY_REGULAR, **params)
        logger.info(f"SELL order placed: {symbol} × {quantity} @ {price} → Order ID: {order_id}")
        return order_id

    @staticmethod
    def place_sl_order(
        symbol: str,
        transaction_type: str,   # "BUY" or "SELL"
        quantity: int,
        trigger_price: float,
        price: float,
        exchange: str = "NSE",
    ) -> str:
        """Stoploss order — triggers at trigger_price, executes at price (SL-L)."""
        kite = kite_session.kite
        tx = kite.TRANSACTION_TYPE_BUY if transaction_type == "BUY" else kite.TRANSACTION_TYPE_SELL
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            tradingsymbol=symbol,
            exchange=exchange,
            transaction_type=tx,
            quantity=quantity,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_SL,
            price=price,
            trigger_price=trigger_price,
            validity=kite.VALIDITY_DAY,
        )
        logger.info(f"SL order placed: {symbol} × {quantity} trigger={trigger_price} → {order_id}")
        return order_id

    @staticmethod
    def place_market_order(
        symbol: str,
        transaction_type: str,
        quantity: int,
        exchange: str = "NSE",
    ) -> str:
        kite = kite_session.kite
        tx = kite.TRANSACTION_TYPE_BUY if transaction_type == "BUY" else kite.TRANSACTION_TYPE_SELL
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            tradingsymbol=symbol,
            exchange=exchange,
            transaction_type=tx,
            quantity=quantity,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_MARKET,
            validity=kite.VALIDITY_DAY,
        )
        logger.info(f"MARKET order placed: {symbol} × {quantity} → {order_id}")
        return order_id

    @staticmethod
    def setup_trade_gtt(
        symbol: str,
        direction: str,    # "LONG" or "SHORT"
        quantity: int,
        ltp: float,
        stop_loss: float,
        target: float,
        exchange: str = "NSE",
    ) -> int:
        """
        High-level GTT for a new trade.
        For LONG: SELL at SL (stop-loss) and SELL at target (take-profit).
        For SHORT: BUY at SL and BUY at target.
        Uses two-leg GTT so the first trigger cancels the second.
        """
        exit_tx = "SELL" if direction == "LONG" else "BUY"
        sl_order = {
            "transaction_type": exit_tx,
            "quantity": quantity,
            "order_type": "LIMIT",
            "product": "MIS",
            "price": stop_loss,
        }
        target_order = {
            "transaction_type": exit_tx,
            "quantity": quantity,
            "order_type": "LIMIT",
            "product": "MIS",
            "price": target,
        }
        # Two-leg: [sl_trigger, target_trigger] — whichever fires first
        trigger_values = [stop_loss, target]
        orders_list = [sl_order, target_order]
        return OrderManager.set_gtt(
            symbol=symbol,
            exchange=exchange,
            trigger_type="two-leg",
            ltp=ltp,
            trigger_values=trigger_values,
            last_prices=[stop_loss, target],
            orders=orders_list,
        )

    @staticmethod
    def set_gtt(
        symbol: str,
        exchange: str,
        trigger_type: str,   # "single" or "two-leg"
        ltp: float,
        trigger_values: list[float],
        last_prices: list[float],
        orders: list[dict],
    ) -> int:
        """Place a GTT (Good Till Triggered) order — for SL + Target simultaneously."""
        kite = kite_session.kite
        gtt_id = kite.place_gtt(
            trigger_type=trigger_type,
            tradingsymbol=symbol,
            exchange=exchange,
            trigger_values=trigger_values,
            last_price=ltp,
            orders=orders,
        )
        logger.info(f"GTT placed: {symbol} triggers={trigger_values} → GTT ID: {gtt_id}")
        return gtt_id

    @staticmethod
    def cancel_order(order_id: str, variety: str = "regular") -> str:
        kite = kite_session.kite
        result = kite.cancel_order(variety=variety, order_id=order_id)
        logger.info(f"Order cancelled: {order_id}")
        return result

    @staticmethod
    def modify_order(
        order_id: str,
        price: float = None,
        quantity: int = None,
        trigger_price: float = None,
        variety: str = "regular",
    ) -> str:
        kite = kite_session.kite
        params = {}
        if price is not None:
            params["price"] = price
        if quantity is not None:
            params["quantity"] = quantity
        if trigger_price is not None:
            params["trigger_price"] = trigger_price
        result = kite.modify_order(variety=variety, order_id=order_id, **params)
        logger.info(f"Order modified: {order_id} params={params}")
        return result

    @staticmethod
    def get_order_status(order_id: str) -> dict:
        kite = kite_session.kite
        orders = kite.orders()
        for o in orders:
            if o["order_id"] == order_id:
                return o
        return {}

    @staticmethod
    def squareoff_all_positions():
        """Emergency square-off all open MIS positions (3:25 PM)."""
        kite = kite_session.kite
        positions = kite.positions()
        day_positions = positions.get("day", [])
        for pos in day_positions:
            if pos["product"] == "MIS" and pos["quantity"] != 0:
                qty = abs(pos["quantity"])
                tx = "SELL" if pos["quantity"] > 0 else "BUY"
                try:
                    OrderManager.place_market_order(
                        symbol=pos["tradingsymbol"],
                        transaction_type=tx,
                        quantity=qty,
                        exchange=pos["exchange"],
                    )
                    logger.warning(f"AUTO SQUAREOFF: {tx} {qty} {pos['tradingsymbol']}")
                except Exception as e:
                    logger.critical(f"Squareoff FAILED for {pos['tradingsymbol']}: {e}")


order_manager = OrderManager()

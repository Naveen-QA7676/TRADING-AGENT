"""
Terminal API — full trading terminal: live quotes, order book, order placement.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from backend.broker.kite_auth import kite_session
from backend.broker.orders import order_manager

router = APIRouter(prefix="/terminal", tags=["terminal"])


class OrderRequest(BaseModel):
    symbol: str
    transaction_type: str    # BUY or SELL
    quantity: int
    price: float = 0.0       # 0 = market order
    trigger_price: float = 0.0
    product: str = "MIS"
    order_type: str = "LIMIT"


class GTTRequest(BaseModel):
    symbol: str
    direction: str
    quantity: int
    stop_loss: float
    target: float
    ltp: float


@router.get("/quote/{symbol}")
async def get_live_quote(symbol: str):
    """Real-time quote with OHLC, volume, depth."""
    try:
        quote = kite_session.get_quote([f"NSE:{symbol}"])
        data = quote.get(f"NSE:{symbol}", {})
        depth = kite_session.get_market_depth(symbol)
        return {
            "symbol": symbol,
            "ltp": data.get("last_price"),
            "ohlc": data.get("ohlc", {}),
            "volume": data.get("volume"),
            "change": data.get("net_change"),
            "depth": depth,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/order")
async def place_order(body: OrderRequest):
    """Place a manual order from the terminal."""
    try:
        if body.transaction_type.upper() == "BUY":
            if body.price > 0:
                order_id = order_manager.place_buy_order(body.symbol, body.quantity, body.price)
            else:
                order_id = order_manager.place_market_order(body.symbol, "BUY", body.quantity)
        else:
            if body.price > 0:
                order_id = order_manager.place_sell_order(body.symbol, body.quantity, body.price)
            else:
                order_id = order_manager.place_market_order(body.symbol, "SELL", body.quantity)
        return {"status": "ORDER_PLACED", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gtt")
async def set_gtt(body: GTTRequest):
    """Set a GTT order (stop loss + target pair)."""
    try:
        gtt_id = order_manager.set_gtt(
            symbol=body.symbol,
            direction=body.direction,
            quantity=body.quantity,
            stop_loss=body.stop_loss,
            target=body.target,
            ltp=body.ltp,
        )
        return {"status": "GTT_SET", "gtt_id": gtt_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_orders():
    """All orders placed today."""
    try:
        orders = kite_session.kite.orders()
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/order/{order_id}")
async def cancel_order(order_id: str):
    """Cancel a pending order."""
    try:
        order_manager.cancel_order(order_id)
        return {"status": "CANCELLED", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/margins")
async def get_margins():
    """Available margin/funds."""
    try:
        margins = kite_session.kite.margins()
        equity = margins.get("equity", {})
        return {
            "available": equity.get("available", {}).get("live_balance", 0),
            "used": equity.get("utilised", {}).get("debits", 0),
            "net": equity.get("net", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

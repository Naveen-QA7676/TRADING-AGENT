"""
Positions API — live positions, P&L, partial exit, manual square-off.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from loguru import logger

from backend.database import get_db
from backend.models import Position, DailyPnL
from backend.broker.orders import order_manager
from backend.broker.kite_auth import kite_session
from backend.redis_client import redis_client, KEYS
import json

router = APIRouter(prefix="/positions", tags=["positions"])


class PartialExitRequest(BaseModel):
    position_id: int
    quantity: int
    price: float = 0.0  # 0 = market order


@router.get("/")
async def get_positions(db: AsyncSession = Depends(get_db)):
    """All currently open positions."""
    result = await db.execute(
        select(Position)
        .where(Position.is_open == True)
        .order_by(desc(Position.entry_time))
    )
    positions = result.scalars().all()
    return [_serialize(p) for p in positions]


@router.get("/live")
async def get_live_positions():
    """Live positions from Redis (real-time, updated every 2 seconds)."""
    raw = await redis_client.get(KEYS["open_positions_count"])
    count = int(raw) if raw else 0
    positions_raw = await redis_client.get("positions:live")
    positions = json.loads(positions_raw) if positions_raw else []
    return {"count": count, "positions": positions}


@router.get("/daily-pnl")
async def get_daily_pnl(db: AsyncSession = Depends(get_db)):
    """Today's P&L summary."""
    from datetime import date
    result = await db.execute(
        select(DailyPnL).where(DailyPnL.date == date.today())
    )
    pnl = result.scalar_one_or_none()
    if not pnl:
        return {"date": str(date.today()), "total_pnl": 0, "trade_count": 0}
    return {
        "date": str(pnl.date),
        "total_pnl": pnl.total_pnl,
        "gross_pnl": pnl.gross_pnl,
        "charges": pnl.total_charges,
        "trade_count": pnl.trade_count,
        "win_count": pnl.win_count,
        "loss_count": pnl.loss_count,
    }


@router.post("/partial-exit")
async def partial_exit(body: PartialExitRequest, db: AsyncSession = Depends(get_db)):
    """Partially exit an open position."""
    result = await db.execute(
        select(Position).where(Position.id == body.position_id)
    )
    pos = result.scalar_one_or_none()
    if not pos or not pos.is_open:
        raise HTTPException(status_code=404, detail="Position not found or already closed")

    if body.quantity > pos.quantity:
        raise HTTPException(status_code=400, detail=f"Can only exit up to {pos.quantity} shares")

    try:
        if body.price > 0:
            order_id = order_manager.place_sell_order(
                symbol=pos.symbol,
                quantity=body.quantity,
                price=body.price,
            )
        else:
            order_id = order_manager.place_market_order(
                symbol=pos.symbol,
                transaction_type="SELL",
                quantity=body.quantity,
            )
        return {"status": "ORDER_PLACED", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/squareoff-all")
async def squareoff_all():
    """Emergency square-off all open positions at market price."""
    try:
        order_manager.squareoff_all_positions()
        return {"status": "SQUAREOFF_INITIATED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{position_id}/move-sl-to-entry")
async def move_sl_to_entry(position_id: int, db: AsyncSession = Depends(get_db)):
    """Move stop loss to entry price (breakeven stop)."""
    result = await db.execute(select(Position).where(Position.id == position_id))
    pos = result.scalar_one_or_none()
    if not pos or not pos.is_open:
        raise HTTPException(status_code=404, detail="Position not found")

    try:
        # Cancel existing GTT and reset with SL at entry
        new_gtt = order_manager.set_gtt(
            symbol=pos.symbol,
            direction=pos.direction,
            quantity=pos.quantity,
            stop_loss=pos.avg_price,
            target=pos.target_1,
            ltp=pos.current_price or pos.avg_price,
        )
        pos.stop_loss = pos.avg_price
        await db.commit()
        return {"status": "SL_MOVED_TO_ENTRY", "new_sl": pos.avg_price, "gtt_id": new_gtt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _serialize(p: Position) -> dict:
    return {
        "id": p.id,
        "symbol": p.symbol,
        "direction": p.direction,
        "quantity": p.quantity,
        "avg_price": p.avg_price,
        "current_price": p.current_price,
        "unrealized_pnl": p.unrealized_pnl,
        "unrealized_pnl_pct": p.unrealized_pnl_pct,
        "stop_loss": p.stop_loss,
        "target_1": p.target_1,
        "target_2": p.target_2,
        "mae": p.mae,
        "mfe": p.mfe,
        "entry_time": p.entry_time.isoformat() if p.entry_time else None,
    }

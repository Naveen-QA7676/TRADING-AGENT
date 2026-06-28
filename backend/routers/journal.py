"""
Journal API — trade journal entries, performance analytics, equity curve.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import date, timedelta

from backend.database import get_db
from backend.models import Trade, Journal
from backend.agents.risk_and_learning.performance_analytics import performance_analytics

router = APIRouter(prefix="/journal", tags=["journal"])


class JournalEntry(BaseModel):
    trade_id: int
    mood: str = ""
    notes: str = ""
    lesson: str = ""
    rating: int = 3  # 1–5


@router.get("/trades")
async def get_trades(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Recent closed trades for journal view."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(Trade)
        .where(Trade.entry_time >= since)
        .order_by(desc(Trade.entry_time))
    )
    trades = result.scalars().all()
    return [_serialize_trade(t) for t in trades]


@router.get("/stats")
async def get_performance_stats(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Full performance statistics."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(Trade).where(Trade.entry_time >= since)
    )
    trades = result.scalars().all()
    trade_dicts = [_serialize_trade(t) for t in trades]
    stats = performance_analytics.compute_from_trades(trade_dicts)
    return {
        "period_days": days,
        "total_trades": stats.total_trades,
        "wins": stats.wins,
        "losses": stats.losses,
        "win_rate": stats.win_rate,
        "expectancy": stats.expectancy,
        "profit_factor": stats.profit_factor,
        "sharpe_ratio": stats.sharpe_ratio,
        "max_drawdown": stats.max_drawdown,
        "best_setup": stats.best_setup,
        "worst_setup": stats.worst_setup,
        "best_time": stats.best_time,
        "by_setup": stats.by_setup,
        "by_hour": stats.by_hour,
        "equity_curve": stats.equity_curve,
        "r_distribution": stats.r_distribution,
    }


@router.post("/entry")
async def add_journal_entry(body: JournalEntry, db: AsyncSession = Depends(get_db)):
    """Add a journal entry for a trade."""
    entry = Journal(
        trade_id=body.trade_id,
        mood=body.mood,
        notes=body.notes,
        lesson=body.lesson,
        rating=body.rating,
    )
    db.add(entry)
    await db.commit()
    return {"status": "CREATED", "id": entry.id}


@router.get("/entries")
async def get_journal_entries(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Journal).order_by(desc(Journal.created_at)).limit(limit)
    )
    return [
        {
            "id": j.id,
            "trade_id": j.trade_id,
            "mood": j.mood,
            "notes": j.notes,
            "lesson": j.lesson,
            "rating": j.rating,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in result.scalars().all()
    ]


def _serialize_trade(t: Trade) -> dict:
    return {
        "id": t.id,
        "symbol": t.symbol,
        "direction": t.direction,
        "strategy_name": t.strategy_name,
        "quantity": t.quantity,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "gross_pnl": t.gross_pnl,
        "net_pnl": t.net_pnl,
        "r_multiple": t.r_multiple,
        "confidence_score": t.confidence_score,
        "regime": t.regime,
        "trade_type": t.trade_type,
        "entry_time": t.entry_time.isoformat() if t.entry_time else None,
        "exit_time": t.exit_time.isoformat() if t.exit_time else None,
    }

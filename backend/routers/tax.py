"""
Tax API — P&L reports, charges, turnover, ITR summary download.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date, timedelta

from backend.database import get_db
from backend.models import Trade, TaxRecord
from backend.tax.tax_calculator import tax_calculator
from backend.tax.turnover_tracker import turnover_tracker
from backend.tax.brokerage_tracker import brokerage_tracker
from backend.tax.report_generator import report_generator

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/summary")
async def get_tax_summary(
    fy: str = Query("2025-26"),
    db: AsyncSession = Depends(get_db),
):
    """Full tax summary for the financial year."""
    trades = await _get_fy_trades(fy, db)
    pnl_report = report_generator.generate_pnl_report(trades, fy=fy)
    ts = turnover_tracker.get_summary(fy=fy)

    charges_list = [
        brokerage_tracker.compute(
            symbol=t.get("symbol", ""),
            trade_date=str(t.get("entry_time") or ""),
            trade_type=t.get("trade_type", "INTRADAY"),
            quantity=t.get("quantity", 0),
            buy_price=t.get("entry_price", 0),
            sell_price=t.get("exit_price", 0),
            gross_pnl=t.get("gross_pnl", 0),
        )
        for t in trades
    ]
    charges_summary = brokerage_tracker.annual_charges_summary(charges_list)

    return {
        "fy": fy,
        "pnl_report": pnl_report,
        "turnover": {
            "speculative": ts.speculative_turnover,
            "delivery": ts.delivery_turnover,
            "total": ts.total_turnover,
            "audit_required": ts.audit_required,
            "gst_required": ts.gst_registration_required,
        },
        "charges": charges_summary,
    }


@router.get("/download/pnl-csv")
async def download_pnl_csv(fy: str = Query("2025-26"), db: AsyncSession = Depends(get_db)):
    """Download P&L tradebook as CSV."""
    trades = await _get_fy_trades(fy, db)
    csv_data = report_generator.generate_tradebook_csv(trades)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pnl_{fy}.csv"},
    )


@router.get("/download/itr-summary")
async def download_itr_summary(fy: str = Query("2025-26"), db: AsyncSession = Depends(get_db)):
    """Download ITR filing summary as plain text."""
    trades = await _get_fy_trades(fy, db)
    pnl_report = report_generator.generate_pnl_report(trades, fy=fy)
    ts = turnover_tracker.get_summary(fy=fy)

    charges_list = [
        brokerage_tracker.compute(
            symbol=t.get("symbol", ""),
            trade_date=str(t.get("entry_time") or ""),
            trade_type=t.get("trade_type", "INTRADAY"),
            quantity=t.get("quantity", 0),
            buy_price=t.get("entry_price", 0),
            sell_price=t.get("exit_price", 0),
            gross_pnl=t.get("gross_pnl", 0),
        )
        for t in trades
    ]
    charges_summary = brokerage_tracker.annual_charges_summary(charges_list)
    summary_text = report_generator.generate_itr_summary(pnl_report, ts, charges_summary)

    return Response(
        content=summary_text,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=itr_summary_{fy}.txt"},
    )


@router.get("/monthly")
async def get_monthly_breakdown(fy: str = Query("2025-26"), db: AsyncSession = Depends(get_db)):
    """Monthly P&L breakdown."""
    trades = await _get_fy_trades(fy, db)
    monthly: dict[str, float] = {}
    for t in trades:
        entry_time = t.get("entry_time")
        if entry_time:
            month_key = str(entry_time)[:7]  # YYYY-MM
            monthly[month_key] = monthly.get(month_key, 0) + (t.get("net_pnl") or 0)
    return {"fy": fy, "monthly": dict(sorted(monthly.items()))}


async def _get_fy_trades(fy: str, db: AsyncSession) -> list[dict]:
    """Helper: fetch all closed trades for a financial year."""
    fy_start_year = int(fy.split("-")[0])
    fy_start = date(fy_start_year, 4, 1)
    fy_end = date(fy_start_year + 1, 3, 31)

    result = await db.execute(
        select(Trade)
        .where(Trade.entry_time >= fy_start)
        .where(Trade.entry_time <= fy_end)
        .where(Trade.exit_time != None)
        .order_by(Trade.entry_time)
    )
    trades = result.scalars().all()
    return [
        {
            "symbol": t.symbol,
            "trade_type": t.trade_type or "INTRADAY",
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "gross_pnl": t.gross_pnl,
            "net_pnl": t.net_pnl,
            "charges": t.total_charges,
            "r_multiple": t.r_multiple,
            "confidence_score": t.confidence_score,
            "regime": t.regime,
            "strategy_name": t.strategy_name,
            "direction": t.direction,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
        }
        for t in trades
    ]

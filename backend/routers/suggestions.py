"""
Suggestions API — GET latest suggestions, POST yes/no decision.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from loguru import logger

from backend.database import get_db
from backend.models import TradeSuggestion
from backend.redis_client import redis_client, KEYS
from backend.agents.execution_intelligence.execution_agent import execution_agent

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


class DecisionRequest(BaseModel):
    suggestion_id: int
    decision: str  # "YES" or "NO"
    notes: str = ""


@router.get("/")
async def get_suggestions(db: AsyncSession = Depends(get_db)):
    """Get all pending suggestions (status=PENDING)."""
    result = await db.execute(
        select(TradeSuggestion)
        .where(TradeSuggestion.status == "PENDING")
        .order_by(desc(TradeSuggestion.created_at))
        .limit(10)
    )
    suggestions = result.scalars().all()
    return [_serialize(s) for s in suggestions]


@router.get("/latest")
async def get_latest():
    """Get latest suggestion from Redis (fastest, for live polling)."""
    raw = await redis_client.get(KEYS["suggestion"])
    if not raw:
        return {"suggestion": None}
    import json
    return {"suggestion": json.loads(raw)}


@router.get("/{suggestion_id}")
async def get_suggestion(suggestion_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TradeSuggestion).where(TradeSuggestion.id == suggestion_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return _serialize(s)


@router.post("/{suggestion_id}/decision")
async def submit_decision(
    suggestion_id: int,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """User submits YES or NO."""
    result = await db.execute(
        select(TradeSuggestion).where(TradeSuggestion.id == suggestion_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if s.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Suggestion already {s.status}")

    decision = body.decision.upper()
    if decision not in ("YES", "NO"):
        raise HTTPException(status_code=400, detail="Decision must be YES or NO")

    s.status = "APPROVED" if decision == "YES" else "REJECTED"
    s.user_decision = decision

    execution_result = None
    if decision == "YES":
        suggestion_dict = _serialize(s)
        try:
            execution_result = await execution_agent.execute(suggestion_dict, user_approved=True)
            if execution_result.get("executed"):
                s.status = "EXECUTED"
            else:
                s.status = "EXECUTION_FAILED"
        except Exception as e:
            logger.error(f"Execution error: {e}")
            s.status = "EXECUTION_FAILED"

    await db.commit()
    return {
        "status": s.status,
        "decision": decision,
        "execution": execution_result,
    }


@router.delete("/{suggestion_id}")
async def expire_suggestion(suggestion_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a suggestion as expired (user didn't act in time)."""
    result = await db.execute(
        select(TradeSuggestion).where(TradeSuggestion.id == suggestion_id)
    )
    s = result.scalar_one_or_none()
    if s and s.status == "PENDING":
        s.status = "EXPIRED"
        await db.commit()
    return {"status": "EXPIRED"}


def _serialize(s: TradeSuggestion) -> dict:
    return {
        "id": s.id,
        "symbol": s.symbol,
        "direction": s.direction,
        "strategy_name": s.strategy_name,
        "confidence_score": s.confidence_score,
        "entry_price": s.entry_price,
        "entry_price_low": s.entry_price_low,
        "entry_price_high": s.entry_price_high,
        "stop_loss": s.stop_loss,
        "target_1": s.target_1,
        "target_2": s.target_2,
        "quantity": s.quantity,
        "risk_amount": s.risk_amount,
        "risk_pct": s.risk_pct,
        "rr_ratio": s.rr_ratio,
        "win_probability": s.win_probability,
        "agent_scores": s.agent_scores,
        "reasoning": s.reasoning,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "valid_until": s.valid_until.isoformat() if s.valid_until else None,
    }

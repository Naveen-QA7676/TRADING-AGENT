"""
SQLAlchemy ORM models for the AI Institutional Trading Intelligence Platform.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, JSON, ForeignKey, Enum, Index, Numeric
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


# ─── Enums ────────────────────────────────────────────────────────────────────

class TradeDirection(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class TradeStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OPEN = "OPEN"
    CLOSED_WIN = "CLOSED_WIN"
    CLOSED_LOSS = "CLOSED_LOSS"
    CLOSED_BE = "CLOSED_BE"   # breakeven
    EXPIRED = "EXPIRED"       # suggestion timed out
    CANCELLED = "CANCELLED"

class MarketRegime(str, enum.Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGE_BOUND = "RANGE_BOUND"
    VOLATILE = "VOLATILE"
    COMPRESSING = "COMPRESSING"
    UNKNOWN = "UNKNOWN"

class NewsImpact(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BREAKING = "BREAKING"

class NewsSentiment(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


# ─── Core Trading Models ───────────────────────────────────────────────────────

class TradeSuggestion(Base):
    """Every suggestion the AI system generates."""
    __tablename__ = "trade_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), default="NSE")
    direction = Column(Enum(TradeDirection), nullable=False)
    status = Column(Enum(TradeStatus), default=TradeStatus.SUGGESTED, index=True)

    # Entry zone
    entry_price_low = Column(Numeric(12, 2))
    entry_price_high = Column(Numeric(12, 2))
    entry_price_used = Column(Numeric(12, 2))   # actual fill price

    # Risk levels
    stop_loss = Column(Numeric(12, 2), nullable=False)
    target_1 = Column(Numeric(12, 2), nullable=False)
    target_2 = Column(Numeric(12, 2))
    invalidation_level = Column(Numeric(12, 2))

    # Position sizing
    quantity = Column(Integer)
    capital_deployed = Column(Numeric(14, 2))
    risk_amount = Column(Numeric(12, 2))
    risk_pct = Column(Float)
    rr_ratio = Column(Float)

    # Confidence & scoring
    confidence_score = Column(Integer)          # 0–100
    win_probability = Column(Float)             # 0–1
    stop_probability = Column(Float)
    sideways_probability = Column(Float)

    # Strategy
    strategy_name = Column(String(100))
    market_regime = Column(Enum(MarketRegime))
    setup_conditions = Column(JSON)             # list of conditions met
    reasons_for = Column(JSON)                  # bullish factors
    reasons_against = Column(JSON)              # risk factors

    # Agent scores (JSON dict: {agent_name: score})
    agent_scores = Column(JSON)

    # Technical snapshot at signal time
    indicators_snapshot = Column(JSON)
    chart_pattern = Column(String(100))
    candlestick_pattern = Column(String(100))

    # Historical edge for this exact setup
    historical_win_rate = Column(Float)
    historical_trades_count = Column(Integer)
    historical_avg_win_r = Column(Float)
    historical_avg_loss_r = Column(Float)
    historical_expectancy = Column(Float)

    # Market context
    nifty_bias = Column(String(20))
    banknifty_bias = Column(String(20))
    vix_level = Column(Float)
    fii_net_flow = Column(Float)
    sector_rank = Column(Integer)

    # Expiry
    expires_at = Column(DateTime)

    # User decision
    decision_at = Column(DateTime)
    decision_note = Column(Text)

    # Order details after approval
    order_id = Column(String(50))

    # Relationship
    trade = relationship("Trade", back_populates="suggestion", uselist=False)


class Trade(Base):
    """Executed trades (approved suggestions that went live)."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    suggestion_id = Column(Integer, ForeignKey("trade_suggestions.id"), unique=True)
    suggestion = relationship("TradeSuggestion", back_populates="trade")

    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), default="NSE")
    direction = Column(Enum(TradeDirection))

    entry_price = Column(Numeric(12, 2))
    exit_price = Column(Numeric(12, 2))
    quantity = Column(Integer)
    stop_loss = Column(Numeric(12, 2))
    target_1 = Column(Numeric(12, 2))
    target_2 = Column(Numeric(12, 2))

    entry_time = Column(DateTime, index=True)
    exit_time = Column(DateTime)

    # P&L
    gross_pnl = Column(Numeric(12, 2))
    brokerage = Column(Numeric(10, 2))
    stt = Column(Numeric(10, 2))
    exchange_charges = Column(Numeric(10, 2))
    gst = Column(Numeric(10, 2))
    stamp_duty = Column(Numeric(10, 2))
    total_charges = Column(Numeric(10, 2))
    net_pnl = Column(Numeric(12, 2))

    # R-multiple
    r_multiple = Column(Float)

    # Strategy
    strategy_name = Column(String(100))
    confidence_score = Column(Integer)
    exit_reason = Column(String(100))     # TARGET_1, TARGET_2, STOP_LOSS, MANUAL, SQUAREOFF, NEWS

    # Kite order IDs
    entry_order_id = Column(String(50))
    exit_order_id = Column(String(50))
    sl_order_id = Column(String(50))

    # Journal
    trade_notes = Column(Text)
    mistakes = Column(JSON)

    # Max adverse / favorable excursion
    max_adverse_excursion = Column(Float)
    max_favorable_excursion = Column(Float)

    # Tax classification
    tax_type = Column(String(30))   # SPECULATIVE_INTRADAY, STCG, LTCG

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_trades_symbol_entry", "symbol", "entry_time"),
    )


class Position(Base):
    """Currently open intraday positions."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), unique=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), default="NSE")
    direction = Column(Enum(TradeDirection))
    quantity = Column(Integer)
    entry_price = Column(Numeric(12, 2))
    current_price = Column(Numeric(12, 2))
    stop_loss = Column(Numeric(12, 2))
    target_1 = Column(Numeric(12, 2))
    target_2 = Column(Numeric(12, 2))
    unrealized_pnl = Column(Numeric(12, 2))
    pnl_pct = Column(Float)
    max_adverse_excursion = Column(Float, default=0.0)
    max_favorable_excursion = Column(Float, default=0.0)
    sl_moved_to_entry = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    opened_at = Column(DateTime, default=datetime.utcnow)


class DailyPnL(Base):
    """Daily P&L summary for risk management."""
    __tablename__ = "daily_pnl"

    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False, unique=True, index=True)  # YYYY-MM-DD
    realized_pnl = Column(Numeric(12, 2), default=0)
    unrealized_pnl = Column(Numeric(12, 2), default=0)
    total_charges = Column(Numeric(10, 2), default=0)
    net_pnl = Column(Numeric(12, 2), default=0)
    num_trades = Column(Integer, default=0)
    num_wins = Column(Integer, default=0)
    num_losses = Column(Integer, default=0)
    risk_used_pct = Column(Float, default=0.0)
    trading_disabled = Column(Boolean, default=False)   # hit daily loss limit
    regime = Column(Enum(MarketRegime))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class NewsItem(Base):
    """News items collected and processed by News Intelligence Agent."""
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String(100))
    headline = Column(Text, nullable=False)
    url = Column(Text)
    published_at = Column(DateTime)

    # AI analysis
    sentiment = Column(Enum(NewsSentiment))
    impact = Column(Enum(NewsImpact))
    affected_symbols = Column(JSON)       # ["INFY", "TCS"]
    affected_sectors = Column(JSON)       # ["IT"]
    expected_move_pct = Column(Float)     # e.g. 2.5 for +2.5%
    ai_summary = Column(Text)
    requires_reeval = Column(Boolean, default=False)  # trigger re-evaluation of open positions

    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)

    __table_args__ = (
        Index("ix_news_fetched_impact", "fetched_at", "impact"),
    )


class Journal(Base):
    """Trade journal entries."""
    __tablename__ = "journal"

    id = Column(Integer, primary_key=True)
    date = Column(String(10), index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    entry_type = Column(String(30))  # TRADE_NOTE, DAILY_REVIEW, WEEKLY_REVIEW, MISTAKE, INSIGHT
    content = Column(Text, nullable=False)
    tags = Column(JSON)
    mood_score = Column(Integer)        # 1–10 self-assessed focus/discipline
    created_at = Column(DateTime, default=datetime.utcnow)


class Strategy(Base):
    """Strategy definitions with their rules and performance stats."""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    rules = Column(JSON)                # entry/exit/filter conditions
    regimes_suitable = Column(JSON)     # ["TRENDING_UP", "TRENDING_DOWN"]
    active = Column(Boolean, default=True)

    # Live performance
    total_trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_win_r = Column(Float, default=0.0)
    avg_loss_r = Column(Float, default=0.0)
    expectancy = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)

    # Best/worst conditions
    best_sectors = Column(JSON)
    best_time_range = Column(JSON)      # {"start": "09:20", "end": "11:00"}
    best_market_regime = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentLog(Base):
    """Log of agent outputs for debugging and transparency."""
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True)
    logged_at = Column(DateTime, default=datetime.utcnow, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    suggestion_id = Column(Integer, ForeignKey("trade_suggestions.id"), nullable=True)
    input_data = Column(JSON)
    output_data = Column(JSON)
    confidence_score = Column(Integer)
    processing_time_ms = Column(Integer)
    error = Column(Text)

    __table_args__ = (
        Index("ix_agent_logs_agent_time", "agent_name", "logged_at"),
    )


class TaxRecord(Base):
    """Tax records for ITR export."""
    __tablename__ = "tax_records"

    id = Column(Integer, primary_key=True)
    financial_year = Column(String(10), nullable=False, index=True)  # "2026-27"
    trade_id = Column(Integer, ForeignKey("trades.id"), unique=True)

    symbol = Column(String(20))
    buy_date = Column(String(10))
    sell_date = Column(String(10))
    buy_price = Column(Numeric(12, 2))
    sell_price = Column(Numeric(12, 2))
    quantity = Column(Integer)
    gross_pnl = Column(Numeric(12, 2))
    total_charges = Column(Numeric(10, 2))
    net_pnl = Column(Numeric(12, 2))
    income_type = Column(String(30))    # SPECULATIVE, STCG, LTCG

    # Detailed charges
    brokerage = Column(Numeric(10, 2))
    stt = Column(Numeric(10, 2))
    exchange_charges = Column(Numeric(10, 2))
    gst = Column(Numeric(10, 2))
    stamp_duty = Column(Numeric(10, 2))

    # Turnover contribution (for ₹10Cr audit threshold)
    turnover_contribution = Column(Numeric(14, 2))  # buy + sell value for intraday


class WatchlistItem(Base):
    """User's watchlist."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    exchange = Column(String(10), default="NSE")
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    alert_price = Column(Numeric(12, 2))
    is_active = Column(Boolean, default=True)


class MarketData(Base):
    """Daily market snapshot for macro context."""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True)
    date = Column(String(10), unique=True, index=True)
    nifty_open = Column(Float)
    nifty_high = Column(Float)
    nifty_low = Column(Float)
    nifty_close = Column(Float)
    nifty_volume = Column(Float)
    banknifty_close = Column(Float)
    india_vix = Column(Float)
    fii_net = Column(Float)
    dii_net = Column(Float)
    sp500_close = Column(Float)
    dxy = Column(Float)
    crude_wti = Column(Float)
    gold = Column(Float)
    sgx_nifty_prev = Column(Float)
    regime = Column(Enum(MarketRegime))
    created_at = Column(DateTime, default=datetime.utcnow)

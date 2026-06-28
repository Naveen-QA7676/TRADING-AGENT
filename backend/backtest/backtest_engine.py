"""
Event-driven backtester for the AI Trading Intelligence Platform.

Usage:
    engine = BacktestEngine(capital=150000, risk_per_trade=0.01)
    results = engine.run(df_ohlcv, strategy_fn)

strategy_fn(df_up_to_bar: pd.DataFrame) → TradeSignal | None
    Called on each new bar. Returns a signal if conditions are met.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import numpy as np
import pandas as pd
from loguru import logger


# ─── Types ───────────────────────────────────────────────────────────────────

@dataclass
class TradeSignal:
    direction: str           # "LONG" or "SHORT"
    entry:     float
    stop_loss: float
    target_1:  float
    target_2:  float = 0.0
    strategy:  str = "UNKNOWN"
    confidence: int = 70


@dataclass
class BacktestTrade:
    bar_index:  int
    date:       datetime
    symbol:     str
    direction:  str
    entry:      float
    stop_loss:  float
    target_1:   float
    target_2:   float
    quantity:   int
    risk_amount: float
    # Filled on exit:
    exit_price:  float = 0.0
    exit_date:   datetime | None = None
    exit_reason: str = ""      # "TARGET_1", "TARGET_2", "STOP_LOSS", "TIMEOUT", "EOD"
    pnl:         float = 0.0
    r_multiple:  float = 0.0
    bars_held:   int = 0
    strategy:    str = "UNKNOWN"
    confidence:  int = 70


@dataclass
class BacktestResults:
    symbol:        str
    total_trades:  int = 0
    wins:          int = 0
    losses:        int = 0
    breakevens:    int = 0
    win_rate:      float = 0.0
    expectancy:    float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio:  float = 0.0
    max_drawdown:  float = 0.0
    total_pnl:     float = 0.0
    avg_win:       float = 0.0
    avg_loss:      float = 0.0
    best_trade:    float = 0.0
    worst_trade:   float = 0.0
    avg_bars_held: float = 0.0
    equity_curve:  list[float] = field(default_factory=list)
    trades:        list[BacktestTrade] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Trades: {self.total_trades} | WR: {self.win_rate:.1%} | "
            f"Exp: {self.expectancy:+.2f}R | PF: {self.profit_factor:.2f} | "
            f"Sharpe: {self.sharpe_ratio:.2f} | MaxDD: {self.max_drawdown:.1%} | "
            f"P&L: ₹{self.total_pnl:,.0f}"
        )


# ─── Engine ───────────────────────────────────────────────────────────────────

class BacktestEngine:
    """
    Realistic event-driven backtester.
    - One open position at a time (no pyramiding).
    - Entry on next-bar open after signal (to avoid look-ahead bias).
    - Exits: target_1 hit → move SL to entry (trail), target_2 or EOD closes remainder.
    - Risk-sized: qty = (capital × risk_pct) / (entry - stop_loss)
    - Slippage: configurable (default 0.05% of price).
    """

    def __init__(
        self,
        capital:        float = 150_000,
        risk_per_trade: float = 0.01,       # 1% of capital
        slippage_pct:   float = 0.0005,     # 0.05% slippage
        max_bars_hold:  int   = 20,         # max bars before force-exit
        partial_exit_at_t1: bool = True,    # exit 50% at T1, trail rest
    ):
        self.capital           = capital
        self.risk_per_trade    = risk_per_trade
        self.slippage_pct      = slippage_pct
        self.max_bars_hold     = max_bars_hold
        self.partial_exit_at_t1 = partial_exit_at_t1

    def run(
        self,
        df: pd.DataFrame,
        strategy_fn: Callable[[pd.DataFrame], TradeSignal | None],
        symbol: str = "UNKNOWN",
    ) -> BacktestResults:
        """
        df must have columns: open, high, low, close, volume (index = datetime or int).
        strategy_fn receives the DataFrame sliced UP TO (not including) the current bar.
        """
        if df.empty or len(df) < 10:
            logger.warning(f"Backtest: insufficient data for {symbol}")
            return BacktestResults(symbol=symbol)

        df = df.reset_index(drop=True)
        results = BacktestResults(symbol=symbol)
        equity = self.capital
        results.equity_curve.append(equity)

        open_trade: BacktestTrade | None = None
        t1_hit = False  # whether we've taken partial exit at T1

        for i in range(1, len(df)):
            bar = df.iloc[i]
            bar_date = bar.get("time", bar.get("date", datetime.now()))
            high, low, close, open_p = (
                float(bar["high"]), float(bar["low"]),
                float(bar["close"]), float(bar["open"]),
            )

            # ── Manage open trade ─────────────────────────────────────────
            if open_trade is not None:
                open_trade.bars_held += 1
                exit_price = 0.0
                exit_reason = ""

                # Determine direction-aware SL/target hits using intrabar H/L
                if open_trade.direction == "LONG":
                    if low <= open_trade.stop_loss:
                        exit_price = open_trade.stop_loss
                        exit_reason = "STOP_LOSS"
                    elif high >= open_trade.target_1 and not t1_hit:
                        if self.partial_exit_at_t1:
                            # Partial exit: close 50% at T1, trail SL to entry
                            exit_price  = open_trade.target_1
                            t1_pnl      = (exit_price - open_trade.entry) * (open_trade.quantity // 2)
                            equity      += t1_pnl
                            open_trade.quantity -= open_trade.quantity // 2
                            open_trade.stop_loss = open_trade.entry  # trail to breakeven
                            t1_hit = True
                            results.equity_curve.append(equity)
                            continue
                        else:
                            exit_price  = open_trade.target_1
                            exit_reason = "TARGET_1"
                    elif open_trade.target_2 and high >= open_trade.target_2:
                        exit_price  = open_trade.target_2
                        exit_reason = "TARGET_2"
                else:  # SHORT
                    if high >= open_trade.stop_loss:
                        exit_price = open_trade.stop_loss
                        exit_reason = "STOP_LOSS"
                    elif low <= open_trade.target_1 and not t1_hit:
                        if self.partial_exit_at_t1:
                            exit_price  = open_trade.target_1
                            t1_pnl      = (open_trade.entry - exit_price) * (open_trade.quantity // 2)
                            equity      += t1_pnl
                            open_trade.quantity -= open_trade.quantity // 2
                            open_trade.stop_loss = open_trade.entry
                            t1_hit = True
                            results.equity_curve.append(equity)
                            continue
                        else:
                            exit_price  = open_trade.target_1
                            exit_reason = "TARGET_1"
                    elif open_trade.target_2 and low <= open_trade.target_2:
                        exit_price  = open_trade.target_2
                        exit_reason = "TARGET_2"

                if not exit_reason and open_trade.bars_held >= self.max_bars_hold:
                    exit_price  = close
                    exit_reason = "TIMEOUT"

                if exit_price:
                    open_trade, equity = self._close_trade(
                        open_trade, exit_price, bar_date, exit_reason, equity, results
                    )
                    t1_hit = False
                    results.equity_curve.append(equity)
                    continue

            # ── Look for new signal (only if no open trade) ──────────────
            if open_trade is None:
                try:
                    signal = strategy_fn(df.iloc[:i])
                except Exception as e:
                    logger.debug(f"Strategy function error at bar {i}: {e}")
                    signal = None

                if signal is not None:
                    # Enter on next bar open + slippage
                    slippage = open_p * self.slippage_pct
                    actual_entry = (
                        open_p + slippage if signal.direction == "LONG"
                        else open_p - slippage
                    )
                    risk_per_share = abs(actual_entry - signal.stop_loss)
                    if risk_per_share <= 0:
                        continue
                    max_risk   = self.capital * self.risk_per_trade
                    quantity   = int(max_risk / risk_per_share)
                    if quantity <= 0:
                        continue
                    risk_amount = quantity * risk_per_share

                    open_trade = BacktestTrade(
                        bar_index   = i,
                        date        = bar_date,
                        symbol      = symbol,
                        direction   = signal.direction,
                        entry       = actual_entry,
                        stop_loss   = signal.stop_loss,
                        target_1    = signal.target_1,
                        target_2    = signal.target_2,
                        quantity    = quantity,
                        risk_amount = risk_amount,
                        strategy    = signal.strategy,
                        confidence  = signal.confidence,
                    )
                    t1_hit = False
                    logger.debug(
                        f"Entry: {symbol} {signal.direction} @ {actual_entry:.2f} "
                        f"SL={signal.stop_loss:.2f} T1={signal.target_1:.2f} qty={quantity}"
                    )

            results.equity_curve.append(equity)

        # Force-close if trade still open at end of data
        if open_trade is not None:
            last_bar = df.iloc[-1]
            last_close = float(last_bar["close"])
            last_date  = last_bar.get("time", last_bar.get("date", datetime.now()))
            open_trade, equity = self._close_trade(
                open_trade, last_close, last_date, "EOD", equity, results
            )
            results.equity_curve.append(equity)

        # Compute aggregate stats
        self._compute_stats(results, equity)
        logger.info(f"Backtest complete for {symbol}: {results.summary()}")
        return results

    def _close_trade(
        self,
        trade:  BacktestTrade,
        exit_price: float,
        exit_date:  datetime,
        reason: str,
        equity: float,
        results: BacktestResults,
    ) -> tuple[None, float]:
        slippage = exit_price * self.slippage_pct
        if trade.direction == "LONG":
            actual_exit = exit_price - slippage
            pnl = (actual_exit - trade.entry) * trade.quantity
        else:
            actual_exit = exit_price + slippage
            pnl = (trade.entry - actual_exit) * trade.quantity

        trade.exit_price  = actual_exit
        trade.exit_date   = exit_date
        trade.exit_reason = reason
        trade.pnl         = round(pnl, 2)
        risk = abs(trade.entry - trade.stop_loss) * max(1, trade.quantity)
        trade.r_multiple  = round(pnl / risk, 2) if risk > 0 else 0

        equity += pnl
        results.trades.append(trade)

        if trade.r_multiple > 0.1:
            results.wins += 1
        elif trade.r_multiple < -0.1:
            results.losses += 1
        else:
            results.breakevens += 1

        logger.debug(
            f"Exit: {trade.symbol} {reason} @ {actual_exit:.2f} "
            f"P&L={pnl:+.0f} R={trade.r_multiple:+.2f}"
        )
        return None, equity

    def _compute_stats(self, results: BacktestResults, final_equity: float):
        trades = results.trades
        results.total_trades = len(trades)
        if not trades:
            return

        pnls    = [t.pnl for t in trades]
        r_vals  = [t.r_multiple for t in trades]
        wins    = [p for p in pnls if p > 0]
        losses  = [p for p in pnls if p <= 0]

        results.total_pnl     = sum(pnls)
        results.win_rate      = results.wins / results.total_trades if results.total_trades else 0
        results.avg_win       = float(np.mean(wins))  if wins    else 0
        results.avg_loss      = float(np.mean(losses)) if losses else 0
        results.best_trade    = max(pnls)
        results.worst_trade   = min(pnls)
        results.avg_bars_held = float(np.mean([t.bars_held for t in trades]))

        gross_wins   = sum(wins)
        gross_losses = abs(sum(losses))
        results.profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

        if results.total_trades > 0:
            wr  = results.win_rate
            avg_w = abs(results.avg_win / (results.avg_loss or 1))
            results.expectancy = wr * avg_w - (1 - wr)

        if len(r_vals) > 1:
            avg_r = float(np.mean(r_vals))
            std_r = float(np.std(r_vals))
            results.sharpe_ratio = avg_r / std_r if std_r > 0 else 0

        # Max drawdown on equity curve
        curve = results.equity_curve
        if curve:
            peak = curve[0]
            max_dd = 0.0
            for val in curve:
                if val > peak:
                    peak = val
                dd = (peak - val) / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            results.max_drawdown = max_dd


# ─── Built-in strategies for quick testing ────────────────────────────────────

def vwap_bounce_strategy(df: pd.DataFrame) -> TradeSignal | None:
    """
    VWAP Bounce setup:
    - Price pulls to within 0.1% of VWAP
    - Current candle closes above VWAP (bullish bounce)
    - RSI between 35–55 (not overbought)
    - Volume on bounce bar > 1.5× 20-bar average
    """
    if len(df) < 20:
        return None
    try:
        from backend.technical.indicators import indicator_engine
        ind = indicator_engine.compute_all(df, "15m")

        vwap  = float(getattr(ind, "vwap", None) and ind.vwap.value or 0)
        rsi   = float(getattr(ind, "rsi",  None) and ind.rsi.value  or 50)
        close = float(df["close"].iloc[-1])
        vol   = float(df["volume"].iloc[-1])
        avg_v = float(df["volume"].iloc[-20:].mean())
        atr   = float(getattr(ind, "atr",  None) and ind.atr.value  or close * 0.01)

        if vwap <= 0:
            return None

        at_vwap     = abs(close - vwap) / vwap < 0.001  # within 0.1%
        above_vwap  = close > vwap
        rsi_ok      = 35 <= rsi <= 60
        vol_ok      = vol > avg_v * 1.5

        if at_vwap and above_vwap and rsi_ok and vol_ok:
            sl = vwap - atr * 1.5
            t1 = close + atr * 2
            t2 = close + atr * 3.5
            return TradeSignal(
                direction="LONG", entry=close, stop_loss=sl,
                target_1=t1, target_2=t2, strategy="VWAP Bounce", confidence=72,
            )
    except Exception:
        pass
    return None


def orb_strategy(df: pd.DataFrame, orb_bars: int = 6) -> TradeSignal | None:
    """
    Opening Range Breakout (first 30 min = 2 × 15m bars):
    - Break of the high of the first `orb_bars` bars with volume confirmation
    """
    if len(df) < orb_bars + 2:
        return None
    try:
        orb_range = df.iloc[:orb_bars]
        orb_high  = float(orb_range["high"].max())
        orb_low   = float(orb_range["low"].min())
        close     = float(df["close"].iloc[-1])
        vol       = float(df["volume"].iloc[-1])
        avg_v     = float(df["volume"].iloc[-20:].mean() if len(df) >= 20 else df["volume"].mean())
        atr       = (float(df["high"].iloc[-1]) - float(df["low"].iloc[-1]))

        if close > orb_high * 1.001 and vol > avg_v * 1.5:
            sl = orb_high - atr
            t1 = close + (close - orb_high) * 2
            return TradeSignal(
                direction="LONG", entry=close, stop_loss=sl,
                target_1=t1, strategy="ORB Breakout", confidence=68,
            )
        if close < orb_low * 0.999 and vol > avg_v * 1.5:
            sl = orb_low + atr
            t1 = close - (orb_low - close) * 2
            return TradeSignal(
                direction="SHORT", entry=close, stop_loss=sl,
                target_1=t1, strategy="ORB Breakdown", confidence=65,
            )
    except Exception:
        pass
    return None

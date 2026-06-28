"""
Performance Analytics Agent — Agent 19.
Tracks all historical trades and computes statistical metrics.
Provides expectancy, win rate by setup, best time of day, R-distribution.
"""

import numpy as np
from dataclasses import dataclass, field
from loguru import logger
from sqlalchemy import select
from datetime import datetime, timedelta


@dataclass
class PerformanceStats:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    by_setup: dict = field(default_factory=dict)
    by_hour: dict = field(default_factory=dict)
    by_regime: dict = field(default_factory=dict)
    equity_curve: list[float] = field(default_factory=list)
    r_distribution: list[float] = field(default_factory=list)
    best_setup: str = ""
    worst_setup: str = ""
    best_time: str = ""


class PerformanceAnalyticsAgent:
    name = "Performance Analytics Agent"

    def compute_from_trades(self, trades: list[dict]) -> PerformanceStats:
        """Compute all stats from a list of trade dictionaries."""
        stats = PerformanceStats()

        if not trades:
            return stats

        r_multiples = []
        pnl_values = []
        setups = {}
        hours = {}
        regimes = {}

        for t in trades:
            r = t.get("r_multiple", 0)
            if r is None:
                continue
            r = float(r)
            pnl = t.get("net_pnl", 0) or 0
            setup = t.get("strategy_name", "UNKNOWN") or "UNKNOWN"
            entry_time = t.get("entry_time")
            hour = entry_time.hour if isinstance(entry_time, datetime) else 10
            regime = t.get("regime", "UNKNOWN") or "UNKNOWN"

            r_multiples.append(r)
            pnl_values.append(float(pnl))

            # By setup
            if setup not in setups:
                setups[setup] = {"wins": 0, "losses": 0, "r_sum": 0, "trades": 0}
            setups[setup]["trades"] += 1
            setups[setup]["r_sum"] += r
            if r > 0:
                setups[setup]["wins"] += 1
            else:
                setups[setup]["losses"] += 1

            # By hour
            hour_key = f"{hour:02d}:00"
            if hour_key not in hours:
                hours[hour_key] = {"wins": 0, "losses": 0, "trades": 0}
            hours[hour_key]["trades"] += 1
            if r > 0:
                hours[hour_key]["wins"] += 1
            else:
                hours[hour_key]["losses"] += 1

        if not r_multiples:
            return stats

        wins = [r for r in r_multiples if r > 0]
        losses = [r for r in r_multiples if r <= 0]

        stats.total_trades = len(r_multiples)
        stats.wins = len(wins)
        stats.losses = len(losses)
        stats.win_rate = stats.wins / stats.total_trades if stats.total_trades > 0 else 0
        stats.avg_win_r = np.mean(wins) if wins else 0
        stats.avg_loss_r = abs(np.mean(losses)) if losses else 1
        stats.expectancy = (stats.win_rate * stats.avg_win_r) - ((1 - stats.win_rate) * stats.avg_loss_r)
        gross_wins = sum(wins)
        gross_losses = abs(sum(losses))
        stats.profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")
        stats.r_distribution = r_multiples

        # Equity curve (cumulative R)
        stats.equity_curve = list(np.cumsum(r_multiples))

        # Max drawdown on equity curve
        if stats.equity_curve:
            peak = stats.equity_curve[0]
            max_dd = 0
            for val in stats.equity_curve:
                if val > peak:
                    peak = val
                dd = peak - val
                if dd > max_dd:
                    max_dd = dd
            stats.max_drawdown = max_dd

        # Sharpe ratio (simplified, using R-multiples)
        if len(r_multiples) > 1:
            avg_r = np.mean(r_multiples)
            std_r = np.std(r_multiples)
            stats.sharpe_ratio = avg_r / std_r if std_r > 0 else 0

        # By setup stats
        for setup, data in setups.items():
            win_rate = data["wins"] / data["trades"] if data["trades"] > 0 else 0
            avg_r = data["r_sum"] / data["trades"] if data["trades"] > 0 else 0
            stats.by_setup[setup] = {
                "trades": data["trades"],
                "win_rate": round(win_rate, 3),
                "avg_r": round(avg_r, 2),
                "expectancy": round(win_rate * avg_r, 2) if avg_r > 0 else round(win_rate * avg_r - (1 - win_rate), 2),
            }

        # Best/worst setup
        if stats.by_setup:
            best = max(stats.by_setup.items(), key=lambda x: x[1]["expectancy"])
            worst = min(stats.by_setup.items(), key=lambda x: x[1]["expectancy"])
            stats.best_setup = f"{best[0]} (exp: {best[1]['expectancy']:+.2f}R)"
            stats.worst_setup = f"{worst[0]} (exp: {worst[1]['expectancy']:+.2f}R)"

        # Best hour
        stats.by_hour = {
            h: {
                "trades": v["trades"],
                "win_rate": round(v["wins"] / v["trades"], 3) if v["trades"] > 0 else 0,
            }
            for h, v in hours.items()
        }
        if stats.by_hour:
            best_h = max(stats.by_hour.items(), key=lambda x: x[1]["win_rate"])
            stats.best_time = f"{best_h[0]} (WR: {best_h[1]['win_rate']:.0%})"

        return stats

    def get_historical_edge_for_setup(self, setup: str, regime: str, trades: list[dict]) -> dict:
        """Returns win rate + expectancy for a specific setup in a specific regime."""
        matching = [
            t for t in trades
            if (t.get("strategy_name", "") == setup)
            and (not regime or t.get("regime", "") == regime)
        ]
        if not matching:
            return {"trades": 0, "win_rate": 0.5, "expectancy": 0}

        sub_stats = self.compute_from_trades(matching)
        return {
            "trades": sub_stats.total_trades,
            "win_rate": round(sub_stats.win_rate, 3),
            "avg_win_r": round(sub_stats.avg_win_r, 2),
            "avg_loss_r": round(sub_stats.avg_loss_r, 2),
            "expectancy": round(sub_stats.expectancy, 2),
            "profit_factor": round(sub_stats.profit_factor, 2),
        }


performance_analytics = PerformanceAnalyticsAgent()

"""
Liquidity Agent — Agent 13.
Validates that the stock has sufficient liquidity to enter and exit cleanly.
Checks: spread, depth, slippage estimate, average volume.
"""

import pandas as pd
from loguru import logger
from backend.microstructure.order_book import order_book_analyzer
from backend.microstructure.spread_monitor import SpreadMonitor
from backend.microstructure.slippage_estimator import slippage_estimator


_spread_monitors: dict[str, SpreadMonitor] = {}


def get_spread_monitor(symbol: str) -> SpreadMonitor:
    if symbol not in _spread_monitors:
        _spread_monitors[symbol] = SpreadMonitor()
    return _spread_monitors[symbol]


class LiquidityAgent:
    name = "Liquidity Agent"

    def analyze(
        self,
        symbol: str,
        ltp: float,
        order_book: dict,
        df_5m: pd.DataFrame,
        quantity: int,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "is_tradeable": True,
            "spread_pct": 0.0,
            "spread_status": "UNKNOWN",
            "depth_score": 0.0,
            "imbalance_ratio": 1.0,
            "order_book_pressure": "NEUTRAL",
            "expected_slippage_pct": 0.0,
            "slippage_acceptable": True,
            "avg_volume_5m": 0,
            "description": "",
        }

        try:
            # ── Order book analysis ───────────────────────────────────────
            if order_book:
                oba = order_book_analyzer.analyze(order_book)
                result["spread_pct"] = oba.spread_pct
                result["depth_score"] = oba.depth_score
                result["imbalance_ratio"] = oba.imbalance_ratio
                result["order_book_pressure"] = oba.pressure
                result["bid_wall"] = oba.bid_wall
                result["ask_wall"] = oba.ask_wall

                # Spread monitor
                sm = get_spread_monitor(symbol)
                spread_status = sm.update(oba.spread_pct, oba.best_bid, oba.best_ask)
                result["spread_status"] = spread_status.status
                result["is_tradeable"] = spread_status.is_tradeable

            # ── Slippage estimate ─────────────────────────────────────────
            if df_5m is not None and len(df_5m) > 0 and quantity > 0:
                slippage = slippage_estimator.estimate(
                    ltp=ltp,
                    quantity=quantity,
                    order_book=order_book,
                    df=df_5m,
                )
                result["expected_slippage_pct"] = slippage.expected_slippage_pct
                result["expected_slippage_inr"] = slippage.expected_slippage_inr
                result["slippage_acceptable"] = slippage.is_acceptable
                result["slippage_recommendation"] = slippage.recommendation

                if not slippage.is_acceptable:
                    result["is_tradeable"] = False

            # ── Average volume ────────────────────────────────────────────
            if df_5m is not None and "volume" in df_5m.columns:
                result["avg_volume_5m"] = int(df_5m["volume"].tail(12).mean())

            # ── Score ─────────────────────────────────────────────────────
            score = 5
            status = result["spread_status"]

            if status == "TIGHT":
                score = 9
            elif status == "NORMAL":
                score = 7
            elif status == "WIDE":
                score = 4
                result["is_tradeable"] = False
            elif status == "VERY_WIDE":
                score = 1
                result["is_tradeable"] = False

            if not result["slippage_acceptable"]:
                score -= 2

            if result["imbalance_ratio"] > 1.5:
                score += 1  # buy pressure → easier to enter long
            elif result["imbalance_ratio"] < 0.67:
                score -= 1  # sell pressure

            result["score"] = max(0, min(10, round(score)))
            result["description"] = (
                f"Spread: {result['spread_pct']:.3f}% ({status}) | "
                f"Depth: {result['depth_score']:.0f}/10 | "
                f"Slippage: ~{result['expected_slippage_pct']:.3f}% | "
                f"Pressure: {result['order_book_pressure']} | "
                f"{'✓ TRADEABLE' if result['is_tradeable'] else '✗ NOT TRADEABLE'}"
            )

        except Exception as e:
            logger.error(f"Liquidity Agent error for {symbol}: {e}")
            result["description"] = f"Error: {str(e)}"
            result["score"] = 3

        return result


liquidity_agent = LiquidityAgent()

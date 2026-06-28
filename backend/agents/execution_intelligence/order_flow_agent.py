"""
Order Flow Agent — Agent 11.
Synthesizes tick data, CVD, delta divergence, and order book into an order flow score.
"""

from loguru import logger
from backend.order_flow.cumulative_delta import CVDEngine
from backend.order_flow.delta_divergence import delta_divergence_detector
from backend.microstructure.order_book import order_book_analyzer
from backend.microstructure.spread_monitor import SpreadMonitor
from backend.microstructure.slippage_estimator import slippage_estimator


class OrderFlowAgent:
    name = "Order Flow Agent"

    def analyze(
        self,
        cvd: float,
        cvd_trend: str,
        delta_history: list[float],
        price_history: list[float],
        cvd_history: list[float],
        order_book_depth: dict,
        ltp: float,
        spread_monitor: SpreadMonitor,
        spread_pct: float,
        quantity: int,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "cvd": cvd,
            "cvd_trend": cvd_trend,
            "divergence": "NONE",
            "pressure": "BALANCED",
            "spread_status": "NORMAL",
            "is_tradeable": True,
            "description": "",
        }

        try:
            score = 5

            # CVD analysis
            if cvd_trend == "BUYERS_DOMINANT":
                score += 2
            elif cvd_trend == "SELLERS_DOMINANT":
                score -= 2

            # Divergence check
            div = delta_divergence_detector.detect(price_history, cvd_history, delta_history)
            result["divergence"] = div.divergence_type
            if div.detected and div.divergence_type == "BEARISH":
                score -= 3
                result["divergence_message"] = div.message
            elif div.detected and div.divergence_type == "BULLISH":
                score += 1
                result["divergence_message"] = div.message

            # Order book analysis
            ob = order_book_analyzer.analyze(order_book_depth, ltp)
            result["pressure"] = ob.pressure
            result["bid_ask_ratio"] = ob.imbalance_ratio
            result["bid_wall"] = ob.bid_wall
            result["ask_wall"] = ob.ask_wall

            if ob.pressure == "BUY_PRESSURE":
                score += 1
            elif ob.pressure == "SELL_PRESSURE":
                score -= 1

            # Spread check
            spread_status = spread_monitor.update(ob.spread, spread_pct)
            result["spread_status"] = spread_status.status
            result["spread_pct"] = spread_pct
            result["is_tradeable"] = spread_status.is_tradeable

            if spread_status.status == "TIGHT":
                score += 1
            elif spread_status.status in ["WIDE", "VERY_WIDE"]:
                score -= 2
                result["is_tradeable"] = False

            # Slippage estimate
            slip = slippage_estimator.estimate(
                quantity, ltp, spread_pct,
                ob.bid_total, ob.ask_total, "BUY"
            )
            result["slippage_pct"] = slip.expected_slippage_pct
            result["slippage_acceptable"] = slip.is_acceptable

            if not slip.is_acceptable:
                score -= 1

            score = max(0, min(10, score))
            result["score"] = score

            result["description"] = (
                f"CVD: {cvd:+,.0f} ({cvd_trend}) | "
                f"Divergence: {result['divergence']} | "
                f"Pressure: {ob.pressure} | "
                f"Spread: {spread_pct:.3f}% ({spread_status.status}) | "
                f"Slippage: {slip.expected_slippage_pct:.3f}%"
            )

        except Exception as e:
            logger.error(f"Order Flow Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


order_flow_agent = OrderFlowAgent()

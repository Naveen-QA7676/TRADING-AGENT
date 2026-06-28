"""
Position Sizer Agent — Agent 17.
Applies Kelly Criterion (conservative), 1% fixed risk rule, and volatility scaling.
Returns exact quantity, risk amount, and margin required.
"""

from loguru import logger
from backend.config import settings


class PositionSizerAgent:
    name = "Position Sizer Agent"

    def calculate(
        self,
        capital: float,
        entry_price: float,
        stop_loss: float,
        target_1: float,
        win_rate: float = 0.6,
        avg_win_r: float = 2.0,
        avg_loss_r: float = 1.0,
        atr_ratio: float = 1.0,
        open_positions_count: int = 0,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 7,
            "quantity": 0,
            "risk_per_share": 0.0,
            "risk_amount": 0.0,
            "risk_pct": 0.0,
            "margin_required": 0.0,
            "potential_profit_t1": 0.0,
            "potential_loss": 0.0,
            "kelly_fraction": 0.0,
            "sizing_method": "FIXED_1PCT",
            "size_reduction": 1.0,
            "description": "",
        }

        try:
            risk_per_share = abs(entry_price - stop_loss)
            reward_per_share = abs(target_1 - entry_price)

            if risk_per_share <= 0:
                result["description"] = "Invalid: risk per share is 0"
                result["score"] = 0
                return result

            # ── Fixed 1% risk rule ─────────────────────────────────────────
            max_risk = capital * settings.max_risk_per_trade
            base_qty = int(max_risk / risk_per_share)

            # ── Kelly Criterion (conservative half-kelly) ──────────────────
            rr = reward_per_share / risk_per_share if risk_per_share > 0 else 1
            kelly = (win_rate - ((1 - win_rate) / rr)) if rr > 0 else 0
            half_kelly = max(0, kelly * 0.5)  # half Kelly for safety
            kelly_qty = int(capital * half_kelly / entry_price) if half_kelly > 0 else base_qty

            # Use the more conservative of fixed 1% vs half-Kelly
            quantity = min(base_qty, kelly_qty) if kelly_qty > 0 else base_qty

            # ── Volatility scaling ─────────────────────────────────────────
            size_reduction = 1.0
            if atr_ratio > 1.5:
                size_reduction = 0.5
                quantity = quantity // 2
            elif atr_ratio > 1.2:
                size_reduction = 0.75
                quantity = int(quantity * 0.75)

            # ── Position count scaling ─────────────────────────────────────
            if open_positions_count >= 2:
                size_reduction *= 0.75
                quantity = int(quantity * 0.75)

            quantity = max(1, quantity)

            risk_amount = quantity * risk_per_share
            margin_required = quantity * entry_price * 0.2  # ~20% MIS margin (approximate)

            result["quantity"] = quantity
            result["risk_per_share"] = round(risk_per_share, 2)
            result["risk_amount"] = round(risk_amount, 2)
            result["risk_pct"] = round((risk_amount / capital) * 100, 3)
            result["margin_required"] = round(margin_required, 2)
            result["potential_profit_t1"] = round(quantity * reward_per_share, 2)
            result["potential_loss"] = round(risk_amount, 2)
            result["kelly_fraction"] = round(half_kelly, 4)
            result["size_reduction"] = round(size_reduction, 2)
            result["sizing_method"] = "FIXED_1PCT_HALF_KELLY_MIN"

            # Score: full size = 10, reduced = lower
            if size_reduction == 1.0:
                result["score"] = 9
            elif size_reduction >= 0.75:
                result["score"] = 7
            else:
                result["score"] = 5

            result["description"] = (
                f"Qty: {quantity} | Risk: ₹{risk_amount:,.0f} ({result['risk_pct']:.2f}%) | "
                f"Margin: ₹{margin_required:,.0f} | "
                f"T1 P&L: +₹{result['potential_profit_t1']:,.0f} / −₹{risk_amount:,.0f} | "
                f"Kelly: {half_kelly:.2%} | "
                f"Size factor: {size_reduction:.0%}"
            )

        except Exception as e:
            logger.error(f"Position Sizer Agent error: {e}")
            result["description"] = f"Error: {str(e)}"
            result["score"] = 0

        return result


position_sizer_agent = PositionSizerAgent()

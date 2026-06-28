"""
Risk Manager Agent — Agent 16.
Hard rules: 1% risk, 2% daily limit, max 3 positions, no trade in first 5 min,
auto-square-off at 3:25 PM, ATR volatility check.
"""

from datetime import datetime, time
import pandas as pd
from loguru import logger
from backend.config import settings


class RiskManagerAgent:
    name = "Risk Manager Agent"

    def evaluate(
        self,
        ltp: float,
        stop_loss: float,
        target_1: float,
        daily_pnl: float,
        open_positions_count: int,
        atr_val: float,
        atr_avg: float,
        df_5m: pd.DataFrame | None = None,
        capital: float = None,
    ) -> dict:
        capital = capital or settings.capital
        result = {
            "agent": self.name,
            "score": 10,
            "risk_ok": True,
            "rr_ok": True,
            "position_limit_ok": True,
            "daily_limit_ok": True,
            "time_ok": True,
            "volatility_ok": True,
            "trading_allowed": True,
            "warnings": [],
            "quantity": 0,
            "risk_amount": 0,
            "rr_ratio": 0,
            "size_reduction_factor": 1.0,
            "description": "",
        }

        warnings = []
        deductions = 0

        try:
            # ── Time check ──────────────────────────────────────────────
            now = datetime.now().time()
            no_trade_start = time(9, 15)
            no_trade_end = time(9, 15 + settings.no_trade_buffer_minutes)
            squareoff_time = time(15, 25)

            if now < no_trade_end and now >= no_trade_start:
                result["time_ok"] = False
                result["trading_allowed"] = False
                warnings.append(f"NO TRADE: First {settings.no_trade_buffer_minutes} minutes (9:15-{no_trade_end.strftime('%H:%M')}). Wait for market structure.")
                deductions += 10

            if now >= squareoff_time:
                result["time_ok"] = False
                result["trading_allowed"] = False
                warnings.append("NO TRADE: Past 3:25 PM. Auto square-off time. No new entries.")
                deductions += 10

            # ── Daily P&L limit ─────────────────────────────────────────
            daily_limit = -settings.daily_loss_limit
            if daily_pnl <= daily_limit:
                result["daily_limit_ok"] = False
                result["trading_allowed"] = False
                warnings.append(f"DAILY LOSS LIMIT HIT: ₹{daily_pnl:,.0f} (limit: ₹{daily_limit:,.0f}). Trading DISABLED for today.")
                deductions += 10
            elif daily_pnl <= daily_limit * 0.6:
                warnings.append(f"Daily P&L warning: ₹{daily_pnl:,.0f} ({(-daily_pnl/capital*100):.1f}% loss). Reduce size.")
                deductions += 2

            # ── Position limit ──────────────────────────────────────────
            if open_positions_count >= settings.max_open_positions:
                result["position_limit_ok"] = False
                result["trading_allowed"] = False
                warnings.append(f"MAX POSITIONS: {open_positions_count}/{settings.max_open_positions} open. No new entries until one closes.")
                deductions += 5

            # ── Risk per trade (1%) ─────────────────────────────────────
            risk_per_share = abs(ltp - stop_loss)
            if risk_per_share <= 0:
                result["risk_ok"] = False
                warnings.append("Invalid stop loss — same as entry price")
                deductions += 5
            else:
                max_risk = capital * settings.max_risk_per_trade
                quantity = int(max_risk / risk_per_share)
                risk_amount = quantity * risk_per_share

                result["quantity"] = quantity
                result["risk_amount"] = round(risk_amount, 2)
                result["risk_pct"] = round((risk_amount / capital) * 100, 2)

                if quantity <= 0:
                    result["risk_ok"] = False
                    warnings.append("Stop loss too tight — quantity would be 0")
                    deductions += 5

            # ── R:R ratio ───────────────────────────────────────────────
            if risk_per_share > 0:
                reward = abs(target_1 - ltp)
                rr = reward / risk_per_share
                result["rr_ratio"] = round(rr, 2)
                if rr < 1.5:
                    result["rr_ok"] = False
                    warnings.append(f"R:R ratio {rr:.2f} below minimum 1.5. Improve target or tighten stop.")
                    deductions += 3
                elif rr >= 2.5:
                    deductions -= 1  # bonus for excellent R:R

            # ── ATR volatility check ────────────────────────────────────
            if atr_avg > 0:
                atr_ratio = atr_val / atr_avg
                result["atr_ratio"] = round(atr_ratio, 2)
                if atr_ratio > 1.5:
                    result["size_reduction_factor"] = 0.5
                    result["quantity"] = result["quantity"] // 2
                    result["volatility_ok"] = False
                    warnings.append(f"HIGH VOLATILITY: ATR {atr_ratio:.1f}× avg. Reducing position size by 50%.")
                    deductions += 2
                elif atr_ratio > 1.2:
                    result["size_reduction_factor"] = 0.75
                    result["quantity"] = int(result["quantity"] * 0.75)
                    warnings.append(f"Elevated volatility: ATR {atr_ratio:.1f}× avg. Reducing size 25%.")
                    deductions += 1

            # Final score
            score = max(0, 10 - deductions)
            result["score"] = score
            result["warnings"] = warnings

            if not result["trading_allowed"]:
                result["score"] = 0

            result["description"] = (
                f"Qty: {result['quantity']} | Risk: ₹{result['risk_amount']:,.0f} ({result['risk_pct']:.1f}%) | "
                f"R:R {result['rr_ratio']:.2f} | "
                f"{'⛔ TRADING DISABLED' if not result['trading_allowed'] else '✓ RISK OK'} | "
                f"{'; '.join(warnings[:2]) if warnings else 'All risk checks passed'}"
            )

        except Exception as e:
            logger.error(f"Risk Manager Agent error: {e}")
            result["description"] = f"Error: {str(e)}"
            result["score"] = 0
            result["trading_allowed"] = False

        return result


risk_manager_agent = RiskManagerAgent()

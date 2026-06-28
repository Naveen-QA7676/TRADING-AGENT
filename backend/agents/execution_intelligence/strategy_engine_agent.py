"""
Strategy Engine Agent — Agent 8.
Selects the best strategy for the current market regime + setup.
Validates that all strategy conditions are fully met.
"""

import pandas as pd
from loguru import logger
from backend.technical.setup_detector import setup_detector


class StrategyEngineAgent:
    name = "Strategy Engine Agent"

    STRATEGY_REGIME_MAP = {
        "TRENDING_UP": ["VWAP_BOUNCE", "ORB_BREAKOUT", "EMA_PULLBACK", "PDH_BREAKOUT"],
        "TRENDING_DOWN": ["VWAP_BOUNCE_SHORT", "ORB_BREAKDOWN", "EMA_REJECTION"],
        "RANGE_BOUND": ["SUPPORT_BOUNCE", "RESISTANCE_REJECT", "FIB_RETRACEMENT"],
        "VOLATILE": ["ORB_BREAKOUT"],
        "UNCLEAR": ["VWAP_BOUNCE"],
    }

    def analyze(
        self,
        symbol: str,
        df_5m: pd.DataFrame,
        df_15m: pd.DataFrame,
        df_1h: pd.DataFrame,
        df_daily: pd.DataFrame,
        ltp: float,
        vwap: float,
        poc: float,
        vah: float,
        val: float,
        market_regime: str,
        cvd: float,
        cvd_trend: str,
        volume_ratio: float,
        indicators_5m: dict,
        indicators_15m: dict,
        indicators_1h: dict,
        support_levels: list,
        resistance_levels: list,
        order_blocks: list,
        fvg_list: list,
        fib_support: float = 0,
        fib_resistance: float = 0,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "selected_strategy": None,
            "strategy_conditions_met": False,
            "conditions_check": {},
            "setup_quality": 0,
            "entry_zone_low": 0,
            "entry_zone_high": 0,
            "stop_loss": 0,
            "target_1": 0,
            "target_2": 0,
            "direction": "LONG",
            "description": "",
        }

        try:
            # Detect setups using the setup detector
            setups = setup_detector.detect_setups(
                symbol=symbol,
                df_5m=df_5m,
                df_15m=df_15m,
                df_1h=df_1h,
                df_daily=df_daily,
                ltp=ltp,
                vwap=vwap,
                poc=poc,
                vah=vah,
                val=val,
                cvd=cvd,
                cvd_trend=cvd_trend,
                volume_ratio=volume_ratio,
                indicators_5m=indicators_5m,
                indicators_15m=indicators_15m,
                indicators_1h=indicators_1h,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                order_blocks=order_blocks,
                fvg_list=fvg_list,
                fib_support=fib_support,
                fib_resistance=fib_resistance,
            )

            if not setups:
                result["description"] = "No qualifying setup found for current market conditions."
                result["score"] = 3
                return result

            # Pick best setup (already sorted by quality)
            best_setup = setups[0]

            # Validate against regime
            allowed = self.STRATEGY_REGIME_MAP.get(market_regime, ["VWAP_BOUNCE"])
            regime_match = any(
                s in best_setup.strategy_name.upper().replace(" ", "_")
                for s in allowed
            )

            result["selected_strategy"] = best_setup.strategy_name
            result["strategy_conditions_met"] = best_setup.conditions_met
            result["conditions_check"] = best_setup.conditions_check
            result["setup_quality"] = best_setup.quality_score
            result["entry_zone_low"] = best_setup.entry_low
            result["entry_zone_high"] = best_setup.entry_high
            result["stop_loss"] = best_setup.stop_loss
            result["target_1"] = best_setup.target_1
            result["target_2"] = best_setup.target_2
            result["direction"] = best_setup.direction

            # Score
            score = best_setup.quality_score / 10.0  # normalize to 0–10
            if not regime_match:
                score -= 2
            if not best_setup.conditions_met:
                score -= 3

            result["score"] = max(0, min(10, round(score)))

            conditions_str = " | ".join(
                f"{'✓' if v else '✗'} {k}"
                for k, v in list(best_setup.conditions_check.items())[:4]
            )
            result["description"] = (
                f"Strategy: {best_setup.strategy_name} | "
                f"Quality: {best_setup.quality_score:.0f}/100 | "
                f"Regime fit: {'✓' if regime_match else '✗'} | "
                f"{conditions_str}"
            )

        except Exception as e:
            logger.error(f"Strategy Engine Agent error: {e}")
            result["description"] = f"Error: {str(e)}"
            result["score"] = 0

        return result


strategy_engine_agent = StrategyEngineAgent()

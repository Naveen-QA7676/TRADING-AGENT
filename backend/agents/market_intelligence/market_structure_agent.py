"""
Market Structure Agent — Agent 1.
Classifies market regime, trend structure, and day type.
Determines overall trading bias for the session.
"""

import pandas as pd
from loguru import logger

from backend.technical.market_structure import market_structure_analyzer
from backend.technical.indicators import indicator_engine
from backend.auction.amt_classifier import amt_classifier
from backend.auction.volume_profile import volume_profile_engine


class MarketStructureAgent:
    name = "Market Structure Agent"

    def analyze(
        self,
        df_nifty_15m: pd.DataFrame,
        df_nifty_daily: pd.DataFrame,
        df_stock_15m: pd.DataFrame,
        prev_vah: float = 0,
        prev_val: float = 0,
        prev_poc: float = 0,
        prev_close: float = 0,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "regime": "UNKNOWN",
            "structure": "UNDEFINED",
            "trend": "SIDEWAYS",
            "nifty_bias": "NEUTRAL",
            "stock_bias": "NEUTRAL",
            "bos": False,
            "choch": False,
            "amt_session": "UNKNOWN",
            "volume_profile": {},
            "description": "",
        }

        try:
            # Nifty structure
            nifty_ms = market_structure_analyzer.analyze(df_nifty_15m)
            nifty_ind = indicator_engine.compute_all(df_nifty_15m, "15m")

            # Stock structure
            stock_ms = market_structure_analyzer.analyze(df_stock_15m)

            # Volume Profile
            vp = volume_profile_engine.compute(df_nifty_15m)

            # AMT classification
            if len(df_nifty_15m) > 6:
                amt = amt_classifier.classify_session(
                    df_nifty_15m, prev_vah, prev_val, prev_poc, prev_close
                )
                result["amt_session"] = amt.session_type
                result["balance_state"] = amt.balance_state
                result["opening_type"] = amt.opening_type

            # Score
            score = 5
            if nifty_ms.trend in ["UP", "HH_HL"]:
                score += 2
                result["nifty_bias"] = "BULLISH"
            elif nifty_ms.trend in ["DOWN", "LH_LL"]:
                score -= 2
                result["nifty_bias"] = "BEARISH"

            if stock_ms.trend in ["UP", "HH_HL"]:
                score += 2
                result["stock_bias"] = "BULLISH"
            elif stock_ms.trend in ["DOWN", "LH_LL"]:
                score -= 2
                result["stock_bias"] = "BEARISH"

            if nifty_ind.adx and float(nifty_ind.adx.value or 0) > 25:
                score += 1  # strong trend

            score = max(0, min(10, score))

            # Regime classification
            if nifty_ms.trend in ["UP", "HH_HL"] and float(nifty_ind.adx.value or 0) > 25:
                regime = "TRENDING_UP"
            elif nifty_ms.trend in ["DOWN", "LH_LL"] and float(nifty_ind.adx.value or 0) > 25:
                regime = "TRENDING_DOWN"
            elif nifty_ms.trend == "SIDEWAYS" and float(nifty_ind.adx.value or 0) < 20:
                regime = "RANGE_BOUND"
            elif "VOLATILE" in str(nifty_ms.description):
                regime = "VOLATILE"
            elif "CONTRACTING" in str(nifty_ms.structure_type):
                regime = "COMPRESSING"
            else:
                regime = "UNKNOWN"

            result.update({
                "score": score,
                "regime": regime,
                "structure": nifty_ms.structure_type,
                "trend": nifty_ms.trend,
                "bos": nifty_ms.bos_detected,
                "choch": nifty_ms.choch_detected,
                "last_swing_high": nifty_ms.last_swing_high,
                "last_swing_low": nifty_ms.last_swing_low,
                "volume_profile": {
                    "poc": vp.poc, "vah": vp.vah, "val": vp.val,
                    "hvn": vp.hvn[:3], "lvn": vp.lvn[:3],
                },
                "description": f"Regime: {regime}. Nifty: {nifty_ms.description}. Stock: {stock_ms.description}",
            })

        except Exception as e:
            logger.error(f"Market Structure Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


market_structure_agent = MarketStructureAgent()

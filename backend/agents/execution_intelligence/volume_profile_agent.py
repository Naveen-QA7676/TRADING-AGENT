"""
Volume Profile Agent — Agent 12.
Analyzes POC, VAH, VAL, HVN, LVN relative to current price.
Determines initiative vs responsive activity.
"""

import pandas as pd
from loguru import logger

from backend.auction.volume_profile import volume_profile_engine
from backend.auction.amt_classifier import amt_classifier
from backend.auction.initiative_detector import initiative_detector


class VolumeProfileAgent:
    name = "Volume Profile Agent"

    def analyze(
        self,
        df_intraday: pd.DataFrame,
        df_daily: pd.DataFrame,
        ltp: float,
        cvd: float,
        cvd_trend: str,
        volume_ratio: float,
        prev_vah: float = 0,
        prev_val: float = 0,
        prev_poc: float = 0,
        prev_close: float = 0,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "poc": 0,
            "vah": 0,
            "val": 0,
            "hvn": [],
            "lvn": [],
            "price_position": "INSIDE_VA",
            "activity_type": "AUCTION",
            "at_key_level": False,
            "description": "",
        }

        try:
            # Compute today's session Volume Profile
            vp = volume_profile_engine.compute(df_intraday)
            result["poc"] = vp.poc
            result["vah"] = vp.vah
            result["val"] = vp.val
            result["hvn"] = vp.hvn[:5]
            result["lvn"] = vp.lvn[:5]

            # Price position
            position = volume_profile_engine.price_outside_value_area(vp, ltp)
            result["price_position"] = position

            at_poc = volume_profile_engine.price_at_poc(vp, ltp)
            result["at_poc"] = at_poc

            # Nearest HVN/LVN
            nearest_hvn = volume_profile_engine.nearest_hvn(vp, ltp)
            nearest_lvn = volume_profile_engine.nearest_lvn(vp, ltp)
            result["nearest_hvn"] = nearest_hvn
            result["nearest_lvn"] = nearest_lvn

            # Initiative/Responsive detection
            activity = initiative_detector.detect(
                ltp, vp.poc, vp.vah, vp.val, cvd, cvd_trend, volume_ratio
            )
            result["activity_type"] = activity.category
            result["activity_confidence"] = activity.confidence
            result["trade_implication"] = activity.trade_implication

            # AMT session classification (using daily data for context)
            if len(df_intraday) >= 6 and prev_vah and prev_val:
                amt = amt_classifier.classify_session(
                    df_intraday, prev_vah, prev_val, prev_poc, prev_close
                )
                result["session_type"] = amt.session_type
                result["balance_state"] = amt.balance_state
                result["opening_type"] = amt.opening_type

            # Scoring
            score = 5

            if activity.category == "INITIATIVE_BUY":
                score = 9
            elif activity.category == "RESPONSIVE_BUY":
                score = 8
            elif activity.category == "INITIATIVE_SELL":
                score = 2
            elif activity.category == "RESPONSIVE_SELL":
                score = 3
            else:
                score = 5

            if at_poc:
                score += 1  # POC is always a significant level
                result["at_key_level"] = True

            # LVN above = fast lane for price (bullish if breaking above LVN)
            if nearest_lvn and nearest_lvn > ltp and abs(nearest_lvn - ltp) / ltp < 0.005:
                result["lvn_above"] = nearest_lvn
                result["at_key_level"] = True

            score = max(0, min(10, score))
            result["score"] = score

            result["description"] = (
                f"VP: POC={vp.poc:.2f} VAH={vp.vah:.2f} VAL={vp.val:.2f} | "
                f"Price: {position} | Activity: {activity.category} | "
                f"{'At POC ✓' if at_poc else ''} | "
                f"{activity.description[:80]}"
            )

        except Exception as e:
            logger.error(f"Volume Profile Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


volume_profile_agent = VolumeProfileAgent()

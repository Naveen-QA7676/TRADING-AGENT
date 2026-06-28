"""
Initiative vs Responsive activity detector.
- Initiative buying: aggressive buyers moving price away from value (above VAH)
- Responsive buying: buyers returning to value area (near VAL)
- Initiative selling: aggressive sellers driving price below VAL
- Responsive selling: sellers capping rallies to VAH
"""

from dataclasses import dataclass
from loguru import logger


@dataclass
class ActivityType:
    category: str           # "INITIATIVE_BUY", "INITIATIVE_SELL", "RESPONSIVE_BUY", "RESPONSIVE_SELL", "AUCTION"
    confidence: float       # 0–1
    description: str
    trade_implication: str


class InitiativeDetector:

    def detect(
        self,
        price: float,
        poc: float,
        vah: float,
        val: float,
        cvd: float,
        cvd_trend: str,        # "BUYERS_DOMINANT" / "SELLERS_DOMINANT" / "BALANCED"
        volume_ratio: float,   # current volume / avg volume
    ) -> ActivityType:
        """
        Classify the current price action as initiative or responsive.
        """
        if poc == 0:
            return ActivityType("AUCTION", 0.3, "No volume profile data", "NEUTRAL — await profile build")

        above_va = price > vah
        below_va = price < val
        in_va = val <= price <= vah
        near_poc = abs(price - poc) / poc < 0.003 if poc > 0 else False

        buyers_winning = cvd_trend == "BUYERS_DOMINANT"
        sellers_winning = cvd_trend == "SELLERS_DOMINANT"

        # Initiative buying: price above VAH with buyers controlling CVD
        if above_va and buyers_winning:
            desc = (f"INITIATIVE BUY: Price {price:.2f} broke above VAH {vah:.2f}. "
                    f"CVD confirms buyers ({cvd:+,.0f}). "
                    f"Auction expanding upward — trend day in progress.")
            return ActivityType("INITIATIVE_BUY", 0.88, desc,
                                "Strong buy — trend day breakout. Use momentum strategy.")

        # Initiative selling: price below VAL with sellers controlling CVD
        if below_va and sellers_winning:
            desc = (f"INITIATIVE SELL: Price {price:.2f} broke below VAL {val:.2f}. "
                    f"CVD confirms sellers ({cvd:+,.0f}). "
                    f"Auction expanding downward — bearish trend day.")
            return ActivityType("INITIATIVE_SELL", 0.88, desc,
                                "Avoid longs. Responsive short near any bounce to value.")

        # Responsive buying: price near VAL, buyers stepping in
        if (val <= price <= (val + (vah - val) * 0.3)) and buyers_winning and volume_ratio > 1.2:
            desc = (f"RESPONSIVE BUY: Price {price:.2f} near VAL {val:.2f}. "
                    f"Value buyers stepping in (CVD {cvd:+,.0f}). "
                    f"Classic value area bounce — high probability long.")
            return ActivityType("RESPONSIVE_BUY", 0.78, desc,
                                "Buy at VAL, target POC {poc:.2f} then VAH {vah:.2f}.")

        # Responsive selling: price near VAH, sellers rejecting
        if ((vah - (vah - val) * 0.3) <= price <= vah) and sellers_winning and volume_ratio > 1.2:
            desc = (f"RESPONSIVE SELL: Price {price:.2f} near VAH {vah:.2f}. "
                    f"Value sellers rejecting highs (CVD {cvd:+,.0f}).")
            return ActivityType("RESPONSIVE_SELL", 0.78, desc,
                                "Avoid new longs near VAH. Short scalp possible.")

        # Price at POC — very uncertain, two-sided
        if near_poc:
            desc = (f"PRICE AT POC {poc:.2f} — equilibrium point. "
                    f"CVD: {cvd:+,.0f}. Market undecided. "
                    f"Break above = initiative buy, break below = initiative sell.")
            return ActivityType("AUCTION", 0.5, desc,
                                "Wait for direction to confirm at POC before entering.")

        # Price inside value area, no strong CVD signal
        if in_va:
            desc = (f"Price inside value area (VAL {val:.2f}–VAH {vah:.2f}). "
                    f"Market in auction/balance. Range-bound behavior likely.")
            return ActivityType("AUCTION", 0.4, desc,
                                "Fade extremes of value area. No directional trades.")

        return ActivityType("AUCTION", 0.3, "Unclear market context", "NEUTRAL")


initiative_detector = InitiativeDetector()

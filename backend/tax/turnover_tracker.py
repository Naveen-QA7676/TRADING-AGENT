"""
Turnover Tracker — tracks trading turnover for GST/audit threshold.
For intraday: turnover = sum of absolute P&L per trade (not buy+sell value).
For delivery: turnover = sell value.
Audit threshold: ₹10 Crore.
"""

from dataclasses import dataclass, field
from loguru import logger


AUDIT_THRESHOLD = 10_00_00_000  # ₹10 Crore
GST_THRESHOLD = 20_00_000        # ₹20 lakh for GST registration


@dataclass
class TurnoverSummary:
    fy: str
    speculative_turnover: float
    delivery_turnover: float
    total_turnover: float
    audit_required: bool
    gst_registration_required: bool
    audit_threshold: float = AUDIT_THRESHOLD
    gst_threshold: float = GST_THRESHOLD


class TurnoverTracker:
    """
    Maintains running FY turnover.
    Speculative (intraday MIS): turnover = absolute(P&L) per trade.
    Delivery (CNC): turnover = sale value per transaction.
    """

    def __init__(self):
        self._speculative_turnover: float = 0.0
        self._delivery_turnover: float = 0.0
        self._trades: list[dict] = []

    def add_intraday_trade(self, pnl: float, symbol: str = "", trade_date: str = "") -> None:
        """Add completed intraday trade. Turnover = |P&L|."""
        contribution = abs(pnl)
        self._speculative_turnover += contribution
        self._trades.append({
            "type": "INTRADAY",
            "symbol": symbol,
            "date": trade_date,
            "pnl": pnl,
            "turnover_contribution": contribution,
        })
        if self._speculative_turnover > AUDIT_THRESHOLD * 0.8:
            logger.warning(
                f"Turnover at {self._speculative_turnover/10_000_000:.1f}Cr — "
                "approaching ₹10Cr audit threshold!"
            )

    def add_delivery_trade(self, sell_value: float, symbol: str = "", trade_date: str = "") -> None:
        """Add delivery sell transaction. Turnover = sale value."""
        self._delivery_turnover += sell_value
        self._trades.append({
            "type": "DELIVERY",
            "symbol": symbol,
            "date": trade_date,
            "sell_value": sell_value,
            "turnover_contribution": sell_value,
        })

    def get_summary(self, fy: str = "2025-26") -> TurnoverSummary:
        total = self._speculative_turnover + self._delivery_turnover
        return TurnoverSummary(
            fy=fy,
            speculative_turnover=round(self._speculative_turnover, 2),
            delivery_turnover=round(self._delivery_turnover, 2),
            total_turnover=round(total, 2),
            audit_required=total >= AUDIT_THRESHOLD,
            gst_registration_required=total >= GST_THRESHOLD,
        )

    def reset_fy(self) -> None:
        """Call at start of new financial year (April 1)."""
        self._speculative_turnover = 0.0
        self._delivery_turnover = 0.0
        self._trades = []
        logger.info("Turnover tracker reset for new financial year")

    def get_trades(self) -> list[dict]:
        return self._trades.copy()

    @property
    def speculative_turnover(self) -> float:
        return self._speculative_turnover

    @property
    def total_turnover(self) -> float:
        return self._speculative_turnover + self._delivery_turnover


turnover_tracker = TurnoverTracker()

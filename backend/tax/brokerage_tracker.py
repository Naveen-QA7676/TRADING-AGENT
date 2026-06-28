"""
Brokerage & Charges Tracker — tracks all transaction costs for ITR filing.
Charges: Zerodha brokerage, STT, exchange transaction charges, SEBI fees, GST, stamp duty.
"""

from dataclasses import dataclass


@dataclass
class TradeCharges:
    symbol: str
    trade_date: str
    trade_type: str          # "INTRADAY" or "DELIVERY"
    direction: str           # "BUY" or "SELL"
    quantity: int
    price: float
    turnover: float          # quantity × price
    brokerage: float
    stt: float
    exchange_charge: float
    sebi_fee: float
    gst: float
    stamp_duty: float
    total_charges: float
    net_pnl_after_charges: float = 0.0


class BrokerageTracker:
    """
    Computes exact Zerodha charges for every trade.
    Reference: https://zerodha.com/charges/
    """

    # Zerodha MIS (intraday) brokerage
    INTRADAY_BROKERAGE_RATE = 0.0003   # 0.03% or ₹20 max, whichever lower
    MAX_BROKERAGE_PER_ORDER = 20.0

    # NSE equity intraday
    STT_SELL_INTRADAY = 0.000025       # 0.0025% on sell side only
    STT_DELIVERY_BUY_SELL = 0.001      # 0.1% on both sides

    EXCHANGE_CHARGE_NSE = 0.0000322    # ₹3.22 per lakh (NSE)
    SEBI_FEE = 0.000001                # ₹1 per crore = 0.000001%
    GST_RATE = 0.18                    # 18% on brokerage + exchange charges
    STAMP_DUTY_BUY = 0.00015          # 0.015% on buy side

    def compute(
        self,
        symbol: str,
        trade_date: str,
        trade_type: str,
        quantity: int,
        buy_price: float,
        sell_price: float,
        gross_pnl: float,
    ) -> TradeCharges:
        buy_turnover = quantity * buy_price
        sell_turnover = quantity * sell_price

        if trade_type == "INTRADAY":
            brokerage = self._compute_brokerage(buy_turnover) + self._compute_brokerage(sell_turnover)
            stt = sell_turnover * self.STT_SELL_INTRADAY
            exchange_charge = (buy_turnover + sell_turnover) * self.EXCHANGE_CHARGE_NSE
            stamp_duty = buy_turnover * self.STAMP_DUTY_BUY
        else:
            brokerage = min(buy_turnover * 0.001, 20) + min(sell_turnover * 0.001, 20)
            stt = (buy_turnover + sell_turnover) * self.STT_DELIVERY_BUY_SELL
            exchange_charge = (buy_turnover + sell_turnover) * self.EXCHANGE_CHARGE_NSE
            stamp_duty = buy_turnover * self.STAMP_DUTY_BUY

        sebi_fee = (buy_turnover + sell_turnover) * self.SEBI_FEE
        gst = (brokerage + exchange_charge + sebi_fee) * self.GST_RATE
        total = brokerage + stt + exchange_charge + sebi_fee + gst + stamp_duty
        net_pnl = gross_pnl - total

        return TradeCharges(
            symbol=symbol,
            trade_date=trade_date,
            trade_type=trade_type,
            direction="BUY_SELL",
            quantity=quantity,
            price=(buy_price + sell_price) / 2,
            turnover=sell_turnover,
            brokerage=round(brokerage, 2),
            stt=round(stt, 2),
            exchange_charge=round(exchange_charge, 2),
            sebi_fee=round(sebi_fee, 4),
            gst=round(gst, 2),
            stamp_duty=round(stamp_duty, 2),
            total_charges=round(total, 2),
            net_pnl_after_charges=round(net_pnl, 2),
        )

    def _compute_brokerage(self, turnover: float) -> float:
        return min(turnover * self.INTRADAY_BROKERAGE_RATE, self.MAX_BROKERAGE_PER_ORDER)

    def annual_charges_summary(self, charges_list: list[TradeCharges]) -> dict:
        return {
            "total_brokerage": round(sum(c.brokerage for c in charges_list), 2),
            "total_stt": round(sum(c.stt for c in charges_list), 2),
            "total_exchange": round(sum(c.exchange_charge for c in charges_list), 2),
            "total_gst": round(sum(c.gst for c in charges_list), 2),
            "total_stamp": round(sum(c.stamp_duty for c in charges_list), 2),
            "grand_total": round(sum(c.total_charges for c in charges_list), 2),
            "trade_count": len(charges_list),
        }


brokerage_tracker = BrokerageTracker()

"""
Tax Report Generator — produces ITR-ready reports.
Output formats: JSON (for dashboard), CSV (for CA), Excel (with P&L sheet).
"""

import csv
import io
from datetime import datetime
from loguru import logger
from backend.tax.tax_calculator import tax_calculator
from backend.tax.turnover_tracker import TurnoverSummary
from backend.tax.brokerage_tracker import TradeCharges


class TaxReportGenerator:

    def generate_pnl_report(
        self,
        trades: list[dict],
        fy: str = "2025-26",
    ) -> dict:
        """
        Full P&L report for ITR Schedule BP (Business/Profession) and CG (Capital Gains).
        """
        intraday_pnl = sum(
            t.get("net_pnl", 0) or 0
            for t in trades
            if t.get("trade_type") == "INTRADAY"
        )
        stcg_pnl = sum(
            t.get("net_pnl", 0) or 0
            for t in trades
            if t.get("trade_type") == "STCG"
        )
        ltcg_pnl = sum(
            t.get("net_pnl", 0) or 0
            for t in trades
            if t.get("trade_type") == "LTCG"
        )

        speculative_tax = tax_calculator.compute_speculative_tax(
            speculative_income=max(0, intraday_pnl),
        )
        stcg_tax = tax_calculator.compute_stcg_tax(stcg_pnl) if stcg_pnl > 0 else None
        ltcg_tax = tax_calculator.compute_ltcg_tax(ltcg_pnl) if ltcg_pnl > 0 else None

        total_tax = (
            speculative_tax.total_tax
            + (stcg_tax.total_tax if stcg_tax else 0)
            + (ltcg_tax.total_tax if ltcg_tax else 0)
        )

        return {
            "fy": fy,
            "generated_at": datetime.now().isoformat(),
            "income_summary": {
                "speculative_income": round(intraday_pnl, 2),
                "stcg_income": round(stcg_pnl, 2),
                "ltcg_income": round(ltcg_pnl, 2),
                "total_income": round(intraday_pnl + stcg_pnl + ltcg_pnl, 2),
            },
            "tax_summary": {
                "speculative_tax": speculative_tax.total_tax,
                "stcg_tax": stcg_tax.total_tax if stcg_tax else 0,
                "ltcg_tax": ltcg_tax.total_tax if ltcg_tax else 0,
                "total_tax_liability": round(total_tax, 2),
            },
            "advance_tax": speculative_tax.advance_tax_schedule,
            "itr_form": "ITR-3" if intraday_pnl else "ITR-2",
            "schedule_notes": [
                "Intraday income → Schedule BP (Speculative Business)",
                "STCG → Schedule CG (Short Term Capital Gains, Section 111A)",
                "LTCG → Schedule CG (Long Term Capital Gains, Section 112A)",
                "Speculative loss can only be carried forward for 4 years",
                "LTCG exemption: First ₹1,25,000 tax-free (Budget 2024-25)",
            ],
        }

    def generate_tradebook_csv(self, trades: list[dict]) -> str:
        """Returns CSV string in Zerodha tradebook format for CA submission."""
        output = io.StringIO()
        fieldnames = [
            "Date", "Symbol", "Trade Type", "Direction",
            "Quantity", "Avg Price", "Gross P&L", "Charges", "Net P&L", "R Multiple"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for t in trades:
            writer.writerow({
                "Date": str(t.get("trade_date") or t.get("entry_time", ""))[:10],
                "Symbol": t.get("symbol", ""),
                "Trade Type": t.get("trade_type", "INTRADAY"),
                "Direction": t.get("direction", "LONG"),
                "Quantity": t.get("quantity", 0),
                "Avg Price": t.get("entry_price", 0),
                "Gross P&L": round(t.get("gross_pnl", 0) or 0, 2),
                "Charges": round(t.get("charges", 0) or 0, 2),
                "Net P&L": round(t.get("net_pnl", 0) or 0, 2),
                "R Multiple": round(t.get("r_multiple", 0) or 0, 2),
            })

        return output.getvalue()

    def generate_charges_csv(self, charges_list: list[TradeCharges]) -> str:
        """CSV of all charges for brokerage reconciliation."""
        output = io.StringIO()
        fieldnames = [
            "Date", "Symbol", "Type", "Quantity", "Price",
            "Brokerage", "STT", "Exchange", "SEBI Fee", "GST", "Stamp Duty", "Total"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for c in charges_list:
            writer.writerow({
                "Date": c.trade_date,
                "Symbol": c.symbol,
                "Type": c.trade_type,
                "Quantity": c.quantity,
                "Price": c.price,
                "Brokerage": c.brokerage,
                "STT": c.stt,
                "Exchange": c.exchange_charge,
                "SEBI Fee": c.sebi_fee,
                "GST": c.gst,
                "Stamp Duty": c.stamp_duty,
                "Total": c.total_charges,
            })

        return output.getvalue()

    def generate_itr_summary(
        self,
        pnl_report: dict,
        turnover_summary: TurnoverSummary,
        charges_summary: dict,
    ) -> str:
        """Human-readable summary for CA/ITR filing."""
        r = pnl_report
        ts = turnover_summary
        cs = charges_summary

        return f"""
ITR FILING SUMMARY — FY {r['fy']}
Generated: {r['generated_at'][:10]}

═══════════════════════════════════════
INCOME SUMMARY
═══════════════════════════════════════
Speculative (Intraday) Income : ₹{r['income_summary']['speculative_income']:>12,.2f}
STCG Income                   : ₹{r['income_summary']['stcg_income']:>12,.2f}
LTCG Income                   : ₹{r['income_summary']['ltcg_income']:>12,.2f}
                                ─────────────────
Total Trading Income          : ₹{r['income_summary']['total_income']:>12,.2f}

═══════════════════════════════════════
TAX LIABILITY
═══════════════════════════════════════
Speculative Tax (slab rate)   : ₹{r['tax_summary']['speculative_tax']:>12,.2f}
STCG Tax (20%)                : ₹{r['tax_summary']['stcg_tax']:>12,.2f}
LTCG Tax (12.5% above ₹1.25L): ₹{r['tax_summary']['ltcg_tax']:>12,.2f}
                                ─────────────────
TOTAL TAX LIABILITY           : ₹{r['tax_summary']['total_tax_liability']:>12,.2f}

═══════════════════════════════════════
TURNOVER (FOR AUDIT THRESHOLD)
═══════════════════════════════════════
Speculative Turnover          : ₹{ts.speculative_turnover:>12,.2f}
Delivery Turnover             : ₹{ts.delivery_turnover:>12,.2f}
Total Turnover                : ₹{ts.total_turnover:>12,.2f}
Audit Required (>₹10Cr)      : {'YES — MANDATORY AUDIT' if ts.audit_required else 'No'}
GST Registration Required     : {'YES' if ts.gst_registration_required else 'No'}

═══════════════════════════════════════
CHARGES (DEDUCTIBLE EXPENSES)
═══════════════════════════════════════
Total Brokerage               : ₹{cs.get('total_brokerage', 0):>12,.2f}
Total STT                     : ₹{cs.get('total_stt', 0):>12,.2f}
Total Exchange Charges        : ₹{cs.get('total_exchange', 0):>12,.2f}
Total GST (on brokerage)      : ₹{cs.get('total_gst', 0):>12,.2f}
Total Stamp Duty              : ₹{cs.get('total_stamp', 0):>12,.2f}
                                ─────────────────
Grand Total Charges           : ₹{cs.get('grand_total', 0):>12,.2f}

═══════════════════════════════════════
ITR FORM: {r['itr_form']}
═══════════════════════════════════════
Notes:
{chr(10).join('• ' + n for n in r['schedule_notes'])}
"""


report_generator = TaxReportGenerator()

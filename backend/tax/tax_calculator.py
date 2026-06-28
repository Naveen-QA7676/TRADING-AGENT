"""
Tax Calculator — computes Indian income tax on trading income.
Intraday MIS = Speculative Business Income (taxed at slab rate).
STCG (< 12 months equity delivery) = 15% flat.
LTCG (> 12 months equity delivery) = 10% above ₹1 lakh exemption.
"""

from dataclasses import dataclass


# Income tax slabs FY 2025-26 (new regime, default)
NEW_REGIME_SLABS = [
    (0,        300_000,  0.00),
    (300_000,  700_000,  0.05),
    (700_000,  1_000_000, 0.10),
    (1_000_000, 1_200_000, 0.15),
    (1_200_000, 1_500_000, 0.20),
    (1_500_000, float("inf"), 0.30),
]

OLD_REGIME_SLABS = [
    (0,        250_000,  0.00),
    (250_000,  500_000,  0.05),
    (500_000,  1_000_000, 0.20),
    (1_000_000, float("inf"), 0.30),
]

SURCHARGE_RATES = [
    (5_000_000, 10_000_000, 0.10),
    (10_000_000, 20_000_000, 0.15),
    (20_000_000, 50_000_000, 0.25),
    (50_000_000, float("inf"), 0.37),
]

HEALTH_EDUCATION_CESS = 0.04


@dataclass
class TaxBreakdown:
    income_type: str
    gross_income: float
    deductions: float
    taxable_income: float
    base_tax: float
    surcharge: float
    cess: float
    total_tax: float
    effective_rate: float
    advance_tax_schedule: dict


def compute_slab_tax(income: float, regime: str = "NEW") -> float:
    slabs = NEW_REGIME_SLABS if regime == "NEW" else OLD_REGIME_SLABS
    tax = 0.0
    for low, high, rate in slabs:
        if income <= low:
            break
        taxable = min(income, high) - low
        tax += taxable * rate
    return tax


def compute_surcharge(tax: float, income: float) -> float:
    surcharge_rate = 0.0
    for low, high, rate in SURCHARGE_RATES:
        if low < income <= high:
            surcharge_rate = rate
            break
    return tax * surcharge_rate


class TaxCalculator:

    def compute_speculative_tax(
        self,
        speculative_income: float,
        other_income: float = 0,
        regime: str = "NEW",
    ) -> TaxBreakdown:
        """
        Intraday MIS profits are treated as Speculative Business Income.
        Losses can only be offset against other speculative income (not salary).
        """
        total_income = speculative_income + other_income

        if total_income <= 0:
            return TaxBreakdown(
                income_type="SPECULATIVE",
                gross_income=speculative_income,
                deductions=0,
                taxable_income=0,
                base_tax=0,
                surcharge=0,
                cess=0,
                total_tax=0,
                effective_rate=0,
                advance_tax_schedule={},
            )

        base_tax = compute_slab_tax(total_income, regime)
        surcharge = compute_surcharge(base_tax, total_income)
        cess = (base_tax + surcharge) * HEALTH_EDUCATION_CESS
        total_tax = base_tax + surcharge + cess

        effective_rate = (total_tax / total_income * 100) if total_income > 0 else 0

        return TaxBreakdown(
            income_type="SPECULATIVE",
            gross_income=speculative_income,
            deductions=0,
            taxable_income=total_income,
            base_tax=round(base_tax),
            surcharge=round(surcharge),
            cess=round(cess),
            total_tax=round(total_tax),
            effective_rate=round(effective_rate, 2),
            advance_tax_schedule=self._advance_tax_schedule(total_tax),
        )

    def compute_stcg_tax(self, stcg_profit: float) -> TaxBreakdown:
        """STCG on listed equity/mutual fund: flat 15% (post-Jul 2024 budget: 20%)."""
        # Post-July 23, 2024 Budget: STCG = 20%
        rate = 0.20
        base_tax = max(0, stcg_profit) * rate
        cess = base_tax * HEALTH_EDUCATION_CESS
        total_tax = base_tax + cess

        return TaxBreakdown(
            income_type="STCG",
            gross_income=stcg_profit,
            deductions=0,
            taxable_income=max(0, stcg_profit),
            base_tax=round(base_tax),
            surcharge=0,
            cess=round(cess),
            total_tax=round(total_tax),
            effective_rate=round((total_tax / stcg_profit * 100) if stcg_profit > 0 else 0, 2),
            advance_tax_schedule=self._advance_tax_schedule(total_tax),
        )

    def compute_ltcg_tax(self, ltcg_profit: float) -> TaxBreakdown:
        """LTCG on listed equity: 10% above ₹1 lakh exemption (post-budget 2024: 12.5%)."""
        exemption = 100_000
        taxable = max(0, ltcg_profit - exemption)
        rate = 0.125  # 12.5% post-July 2024
        base_tax = taxable * rate
        cess = base_tax * HEALTH_EDUCATION_CESS
        total_tax = base_tax + cess

        return TaxBreakdown(
            income_type="LTCG",
            gross_income=ltcg_profit,
            deductions=exemption,
            taxable_income=taxable,
            base_tax=round(base_tax),
            surcharge=0,
            cess=round(cess),
            total_tax=round(total_tax),
            effective_rate=round((total_tax / ltcg_profit * 100) if ltcg_profit > 0 else 0, 2),
            advance_tax_schedule=self._advance_tax_schedule(total_tax),
        )

    def _advance_tax_schedule(self, annual_tax: float) -> dict:
        """
        Advance tax due dates (FY 2025-26):
        15% by Jun 15, 45% by Sep 15, 75% by Dec 15, 100% by Mar 15.
        """
        if annual_tax <= 10_000:
            return {"note": "Advance tax not applicable (< ₹10,000)"}
        return {
            "Jun_15": round(annual_tax * 0.15),
            "Sep_15": round(annual_tax * 0.45),
            "Dec_15": round(annual_tax * 0.75),
            "Mar_15": round(annual_tax * 1.00),
            "note": "These are cumulative amounts due by each date",
        }


tax_calculator = TaxCalculator()

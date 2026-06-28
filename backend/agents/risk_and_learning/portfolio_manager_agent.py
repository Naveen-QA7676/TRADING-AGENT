"""
Portfolio Manager Agent — Agent 18.
Manages overall portfolio exposure, sector concentration, and correlation risk.
Enforces max 3 positions, weekly loss limit, and portfolio-level rules.
"""

from loguru import logger
from backend.config import settings
from backend.knowledge.sector_knowledge import SECTOR_MAP


def _get_sector(symbol: str) -> str:
    for sector, data in SECTOR_MAP.items():
        if symbol in data.get("key_stocks", []):
            return sector
    return "DIVERSIFIED"


class PortfolioManagerAgent:
    name = "Portfolio Manager Agent"

    def evaluate(
        self,
        open_positions: list[dict],
        daily_pnl: float,
        weekly_pnl: float,
        capital: float,
        new_symbol: str,
        new_direction: str,
        new_risk_amount: float,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 7,
            "portfolio_ok": True,
            "total_exposure_pct": 0.0,
            "total_risk_pct": 0.0,
            "sector_concentration": {},
            "correlation_risk": "LOW",
            "weekly_loss_ok": True,
            "max_position_ok": True,
            "recommendation": "PROCEED",
            "warnings": [],
            "description": "",
        }

        warnings = []

        try:
            # ── Position count ─────────────────────────────────────────────
            if len(open_positions) >= settings.max_open_positions:
                result["max_position_ok"] = False
                result["portfolio_ok"] = False
                result["recommendation"] = "REJECT"
                warnings.append(f"Max positions ({settings.max_open_positions}) reached")
                result["score"] = 0

            # ── Weekly P&L limit ───────────────────────────────────────────
            weekly_limit = -settings.weekly_loss_limit
            if weekly_pnl <= weekly_limit:
                result["weekly_loss_ok"] = False
                result["portfolio_ok"] = False
                result["recommendation"] = "REJECT"
                warnings.append(
                    f"Weekly loss limit hit: ₹{weekly_pnl:,.0f} "
                    f"(limit: ₹{weekly_limit:,.0f}) — take a break"
                )
                result["score"] = 0

            # ── Sector concentration ───────────────────────────────────────
            sector_map: dict[str, int] = {}
            total_exposure = 0.0
            total_risk = 0.0

            for pos in open_positions:
                sym = pos.get("symbol", "")
                val = pos.get("market_value", 0) or 0
                risk = pos.get("risk_amount", 0) or 0
                sec = _get_sector(sym)
                sector_map[sec] = sector_map.get(sec, 0) + 1
                total_exposure += val
                total_risk += risk

            new_sector = _get_sector(new_symbol)
            sector_map[new_sector] = sector_map.get(new_sector, 0) + 1
            total_risk += new_risk_amount

            result["sector_concentration"] = sector_map
            result["total_exposure_pct"] = round(total_exposure / capital * 100, 2) if capital else 0
            result["total_risk_pct"] = round(total_risk / capital * 100, 2) if capital else 0

            if sector_map.get(new_sector, 0) >= 2:
                warnings.append(f"Sector concentration: {new_sector} already has positions")
                result["score"] -= 2
                result["correlation_risk"] = "HIGH"

            # ── Total risk budget ──────────────────────────────────────────
            if result["total_risk_pct"] > 3.0:
                warnings.append(f"Total portfolio risk {result['total_risk_pct']:.1f}% exceeds 3%")
                result["score"] -= 2

            # ── Same direction check ───────────────────────────────────────
            long_count = sum(1 for p in open_positions if p.get("direction") == "LONG")
            if new_direction == "LONG" and long_count >= 2:
                warnings.append("3 longs = maximum directional exposure")
                result["score"] -= 1

            result["score"] = max(0, min(10, result["score"]))
            result["warnings"] = warnings

            if result["score"] >= 6 and result["portfolio_ok"]:
                result["recommendation"] = "PROCEED"
            elif result["score"] >= 4:
                result["recommendation"] = "PROCEED_WITH_CAUTION"
            else:
                result["recommendation"] = "REJECT"
                result["portfolio_ok"] = False

            result["description"] = (
                f"Positions: {len(open_positions)}/{settings.max_open_positions} | "
                f"Total Risk: {result['total_risk_pct']:.1f}% | "
                f"Weekly P&L: ₹{weekly_pnl:,.0f} | "
                f"Sector: {new_sector} ({sector_map.get(new_sector, 0)} pos) | "
                f"{result['recommendation']}"
            )

        except Exception as e:
            logger.error(f"Portfolio Manager Agent error: {e}")
            result["description"] = f"Error: {str(e)}"
            result["score"] = 3

        return result


portfolio_manager_agent = PortfolioManagerAgent()

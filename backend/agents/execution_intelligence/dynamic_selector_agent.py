"""
Dynamic Selector Agent — Agent 9.
After Scanner produces candidates, this agent picks the BEST ONE to trade right now.
Considers: time of day, open positions, sector overlap, recent trade history.
"""

from datetime import datetime, time
from loguru import logger


class DynamicSelectorAgent:
    name = "Dynamic Selector Agent"

    def select(
        self,
        candidates: list[dict],
        open_positions: list[dict],
        recent_trades_today: list[dict],
        market_regime: str,
        top_sector: str,
    ) -> dict:
        """
        Pick the single best symbol to analyze deeply right now.
        Returns the selected candidate dict or None.
        """
        result = {
            "agent": self.name,
            "score": 5,
            "selected_symbol": None,
            "selection_reason": "",
            "rejected": [],
            "description": "",
        }

        if not candidates:
            result["description"] = "No candidates to select from."
            result["score"] = 0
            return result

        now = datetime.now().time()
        open_symbols = {p.get("symbol") for p in open_positions}
        traded_today = {t.get("symbol") for t in recent_trades_today}
        sector_counts = {}

        for pos in open_positions:
            sec = pos.get("sector", "UNKNOWN")
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

        scored = []
        for c in candidates:
            sym = c.get("symbol", "")
            pre_score = c.get("pre_score", 5)
            sector = c.get("sector", "UNKNOWN")

            penalty = 0
            reasons = []

            # Skip already open
            if sym in open_symbols:
                result["rejected"].append({"symbol": sym, "reason": "Already in open position"})
                continue

            # Avoid same symbol twice in one day
            if sym in traded_today:
                penalty += 2
                reasons.append("Already traded today")

            # Sector concentration: penalize if sector already has a position
            if sector_counts.get(sector, 0) >= 2:
                penalty += 1.5
                reasons.append("Sector concentration risk")

            # Time of day filters
            if now < time(9, 30):
                # Before 9:30, only ORB candidates
                if "ORB" not in c.get("setup_hint", ""):
                    penalty += 1.5

            # Trending regime → prefer momentum setups
            if market_regime == "TRENDING_UP" and c.get("setup_hint", "").startswith("VWAP"):
                pre_score += 1

            final = pre_score - penalty
            scored.append({**c, "final_score": final, "selection_reasons": reasons})

        if not scored:
            result["description"] = "All candidates filtered out (open positions / sector overlap)."
            result["score"] = 2
            return result

        scored.sort(key=lambda x: x["final_score"], reverse=True)
        best = scored[0]

        result["selected_symbol"] = best["symbol"]
        result["score"] = min(10, max(0, round(best["final_score"])))
        result["selection_reason"] = (
            f"Highest combined score {best['final_score']:.1f} | "
            f"Setup: {best.get('setup_hint', 'unknown')} | "
            f"Regime fit ✓"
        )
        result["description"] = (
            f"Selected: {best['symbol']} (score {best['final_score']:.1f}) | "
            f"From {len(candidates)} candidates, {len(scored)} eligible"
        )

        return result


dynamic_selector_agent = DynamicSelectorAgent()

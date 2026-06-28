"""
Sector Rotation Agent — Agent 5.
Ranks all sectors by today's performance + momentum.
Ensures we only trade stocks in top-ranked sectors.
"""

from loguru import logger
from backend.knowledge.sector_knowledge import SECTOR_MAP, SECTOR_ROTATION_CYCLE


class SectorRotationAgent:
    name = "Sector Rotation Agent"

    def analyze(
        self,
        sector_performance: dict[str, float],   # {"BANKING": +0.8, "IT": -0.3, ...}
        symbol: str = None,
        symbol_sector: str = None,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "sector_rankings": [],
            "top_3_sectors": [],
            "bottom_3_sectors": [],
            "symbol_sector_rank": None,
            "is_in_top_sector": False,
            "description": "",
        }

        if not sector_performance:
            result["description"] = "No sector data available"
            return result

        try:
            # Sort sectors by performance
            ranked = sorted(sector_performance.items(), key=lambda x: x[1], reverse=True)
            result["sector_rankings"] = [{"sector": s, "change_pct": round(p, 2)} for s, p in ranked]
            result["top_3_sectors"] = [r["sector"] for r in result["sector_rankings"][:3]]
            result["bottom_3_sectors"] = [r["sector"] for r in result["sector_rankings"][-3:]]

            # Find where our symbol's sector ranks
            if symbol_sector:
                for i, (sector, perf) in enumerate(ranked):
                    if sector.upper() in symbol_sector.upper() or symbol_sector.upper() in sector.upper():
                        rank = i + 1
                        result["symbol_sector_rank"] = rank
                        result["is_in_top_sector"] = rank <= 3
                        break

            # Score
            score = 5
            if result["is_in_top_sector"]:
                rank = result["symbol_sector_rank"]
                if rank == 1:
                    score = 10
                elif rank == 2:
                    score = 8
                elif rank == 3:
                    score = 7
            elif result["symbol_sector_rank"] is not None:
                rank = result["symbol_sector_rank"]
                n = len(ranked)
                score = max(2, 10 - (rank / n) * 8)
            else:
                score = 5

            result["score"] = int(score)

            # Top sectors performance narrative
            top_parts = [f"{s} {p:+.1f}%" for s, p in ranked[:3]]
            result["description"] = (
                f"Top sectors: {', '.join(top_parts)} | "
                f"Symbol sector rank: #{result['symbol_sector_rank']} | "
                f"{'✓ In top sector' if result['is_in_top_sector'] else '⚠ NOT in top sector — reduce confidence'}"
            )

        except Exception as e:
            logger.error(f"Sector Rotation Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


sector_rotation_agent = SectorRotationAgent()

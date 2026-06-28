"""
Micro Intelligence Agent — Agent 3.
Fetches fundamental data from Screener.in and NSE for the candidate stock.
Grades: A+ / A / B / C based on ROE, PE, D/E, promoter holding.
"""

from loguru import logger
from backend.web_research.screener_scraper import screener_scraper
from backend.web_research.nse_scraper import nse_scraper


class MicroIntelligenceAgent:
    name = "Micro Intelligence Agent"

    async def analyze(self, symbol: str) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "symbol": symbol,
            "grade": "B",
            "pe": None,
            "roe": None,
            "roce": None,
            "debt_equity": None,
            "promoter_holding": None,
            "earnings_trend": "UNKNOWN",
            "corporate_actions": [],
            "description": "",
            "cancel_suggestion": False,
        }

        try:
            # Fundamental data from Screener.in
            fundamentals = await screener_scraper.get_fundamentals(symbol)
            if fundamentals:
                result["pe"] = fundamentals.get("pe")
                result["roe"] = fundamentals.get("roe")
                result["roce"] = fundamentals.get("roce")
                result["debt_equity"] = fundamentals.get("debt_equity")
                result["promoter_holding"] = fundamentals.get("promoter_holding")
                result["grade"] = screener_scraper.grade_fundamentals(fundamentals)
                result["earnings_trend"] = fundamentals.get("earnings_trend", "UNKNOWN")

            # Corporate actions from NSE (results today = high volatility)
            try:
                actions = await nse_scraper.get_corporate_actions(symbol)
                result["corporate_actions"] = actions[:3]
                for action in actions:
                    if action.get("type") in ["RESULT", "DIVIDEND", "SPLIT", "BONUS"]:
                        if action.get("ex_date") == "TODAY":
                            result["cancel_suggestion"] = True
                            result["description"] = f"SKIP: {symbol} has {action['type']} today — extreme volatility risk."
                            result["score"] = 0
                            return result
            except Exception:
                pass

            # Score based on fundamental quality
            score = 5
            grade = result["grade"]
            if grade == "A+":
                score = 8
            elif grade == "A":
                score = 7
            elif grade == "B":
                score = 5
            elif grade == "C":
                score = 3

            # Additional checks
            if result["promoter_holding"] and result["promoter_holding"] < 30:
                score -= 1  # Low promoter holding — risk

            if result["debt_equity"] and result["debt_equity"] > 2.0:
                score -= 1  # High debt

            result["score"] = max(0, min(10, score))
            result["description"] = (
                f"Grade: {result['grade']} | PE: {result['pe']} | "
                f"ROE: {result['roe']}% | D/E: {result['debt_equity']} | "
                f"Promoter: {result['promoter_holding']}%"
            )

        except Exception as e:
            logger.error(f"Micro Intelligence Agent error for {symbol}: {e}")
            result["description"] = f"Data unavailable: {str(e)}"

        return result


micro_intelligence_agent = MicroIntelligenceAgent()

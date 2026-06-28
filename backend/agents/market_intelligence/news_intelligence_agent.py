"""
News Intelligence Agent — Agent 4.
Classifies news, extracts affected symbols, and determines if breaking news
requires cancellation of existing suggestions.
"""

import json
from loguru import logger
import anthropic
from backend.config import settings


AFFECTED_SECTORS_MAP = {
    "crude": ["ENERGY", "BPCL", "IOC", "HINDPETRO", "RELIANCE"],
    "rate": ["BANKING", "REALTY", "HDFCBANK", "ICICIBANK"],
    "rupee": ["IT", "PHARMA", "TCS", "INFY"],
    "RBI": ["BANKING", "NBFC"],
    "FII": ["ALL"],
    "budget": ["ALL"],
    "inflation": ["FMCG", "METALS"],
    "US recession": ["IT", "METALS"],
}


class NewsIntelligenceAgent:
    name = "News Intelligence Agent"

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def analyze(self, news_items: list[dict], symbol: str = None) -> dict:
        result = {
            "agent": self.name,
            "score": 7,
            "net_sentiment": "NEUTRAL",
            "impact": "LOW",
            "key_news": [],
            "cancel_suggestion": False,
            "affected_symbols": [],
            "breaking_alerts": [],
            "description": "",
        }

        if not news_items:
            result["description"] = "No news items to analyze"
            return result

        try:
            # Quick rule-based scan first (fast, no API cost)
            bullish_count = 0
            bearish_count = 0
            high_impact = []

            bearish_keywords = [
                "fraud", "scam", "bankruptcy", "arrest", "raid", "SEBI action",
                "downgrade", "warning", "recall", "fine", "penalty", "default",
                "loss", "negative", "profit warning", "guidance cut"
            ]
            bullish_keywords = [
                "record profit", "beat estimates", "upgrade", "buyback", "dividend",
                "strong results", "guidance raised", "deal win", "merger", "acquisition"
            ]
            breaking_keywords = [
                "halt", "circuit", "suspension", "sebi ban", "promoter arrested",
                "fraud detected", "regulatory action"
            ]

            for item in news_items[:30]:
                headline = (item.get("headline", "") + " " + item.get("content", "")).lower()
                is_breaking = any(kw in headline for kw in breaking_keywords)

                if is_breaking:
                    result["cancel_suggestion"] = True
                    result["breaking_alerts"].append({
                        "headline": item.get("headline", ""),
                        "source": item.get("source", ""),
                        "severity": "CRITICAL",
                    })
                    bearish_count += 3

                bull = sum(1 for kw in bullish_keywords if kw in headline)
                bear = sum(1 for kw in bearish_keywords if kw in headline)

                if bull > bear:
                    bullish_count += 1
                    if bull >= 2:
                        high_impact.append({"headline": item.get("headline", ""), "sentiment": "BULLISH"})
                elif bear > bull:
                    bearish_count += 1
                    if bear >= 2:
                        high_impact.append({"headline": item.get("headline", ""), "sentiment": "BEARISH"})

                # Check if news affects our specific symbol
                if symbol and symbol.upper() in (item.get("headline", "") + item.get("content", "")).upper():
                    result["affected_symbols"].append(symbol)
                    if bear > bull:
                        result["cancel_suggestion"] = True

            # Sentiment scoring
            total = bullish_count + bearish_count
            if total > 0:
                bull_pct = bullish_count / total
                if bull_pct > 0.6:
                    result["net_sentiment"] = "BULLISH"
                elif bull_pct < 0.4:
                    result["net_sentiment"] = "BEARISH"

            # Impact assessment
            if high_impact:
                result["impact"] = "HIGH"
                result["key_news"] = high_impact[:5]
            elif total > 5:
                result["impact"] = "MEDIUM"

            # Score
            if result["net_sentiment"] == "BULLISH":
                score = 8
            elif result["net_sentiment"] == "BEARISH":
                score = 3
            else:
                score = 6

            if result["cancel_suggestion"]:
                score = 1

            result["score"] = score
            result["description"] = (
                f"News: {bullish_count} bullish, {bearish_count} bearish | "
                f"Net: {result['net_sentiment']} | Impact: {result['impact']} | "
                f"{'⚠️ BREAKING NEWS — CANCEL SUGGESTION' if result['cancel_suggestion'] else 'Clear'}"
            )

        except Exception as e:
            logger.error(f"News Intelligence Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


news_intelligence_agent = NewsIntelligenceAgent()

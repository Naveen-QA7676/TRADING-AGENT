"""
Sentiment Agent — Agent 7.
Aggregates smart money signals, retail sentiment, and institutional activity.
Looks for divergence between price and institutional flow.
"""

from loguru import logger


class SentimentAgent:
    name = "Sentiment Agent"

    def analyze(
        self,
        fii_net: float,
        dii_net: float,
        pcr: float,
        max_pain: float,
        ltp: float,
        vix: float,
        advance_decline_ratio: float = 1.0,
        nifty_change_pct: float = 0.0,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "smart_money_score": 50,
            "retail_sentiment": "NEUTRAL",
            "institutional_flow": "NEUTRAL",
            "smart_money_bias": "NEUTRAL",
            "divergence_detected": False,
            "divergence_type": None,
            "description": "",
        }

        score = 5
        points = []

        # ── FII/DII institutional flow ────────────────────────────────────
        if fii_net > 1500:
            score += 2
            result["institutional_flow"] = "STRONG_BUY"
            points.append(f"FII strong buy ₹{fii_net:,.0f}Cr")
        elif fii_net > 500:
            score += 1
            result["institutional_flow"] = "BUY"
            points.append(f"FII net buy ₹{fii_net:,.0f}Cr")
        elif fii_net < -1500:
            score -= 2
            result["institutional_flow"] = "STRONG_SELL"
            points.append(f"FII heavy sell ₹{abs(fii_net):,.0f}Cr")
        elif fii_net < -500:
            score -= 1
            result["institutional_flow"] = "SELL"
            points.append(f"FII net sell ₹{abs(fii_net):,.0f}Cr")

        if dii_net > 500:
            score += 0.5
            points.append(f"DII buying ₹{dii_net:,.0f}Cr")

        # ── Options market (retail proxy) ─────────────────────────────────
        # PCR > 1.2 = retail selling puts = bullish (institutions buying calls)
        if pcr > 1.4:
            score += 1.5
            result["retail_sentiment"] = "VERY_BULLISH"
            points.append(f"PCR {pcr:.2f} — heavy put selling (bullish)")
        elif pcr > 1.1:
            score += 0.5
            result["retail_sentiment"] = "BULLISH"
            points.append(f"PCR {pcr:.2f} — bullish bias")
        elif pcr < 0.7:
            score -= 1.5
            result["retail_sentiment"] = "VERY_BEARISH"
            points.append(f"PCR {pcr:.2f} — heavy call buying (bearish)")
        elif pcr < 0.9:
            score -= 0.5
            result["retail_sentiment"] = "BEARISH"
            points.append(f"PCR {pcr:.2f} — bearish bias")
        else:
            result["retail_sentiment"] = "NEUTRAL"

        # ── Max Pain divergence ───────────────────────────────────────────
        if max_pain > 0:
            dist_pct = (ltp - max_pain) / max_pain * 100
            if abs(dist_pct) > 2.0:
                result["divergence_detected"] = True
                result["divergence_type"] = "PRICE_VS_MAX_PAIN"
                if dist_pct > 2:
                    points.append(f"Price {dist_pct:.1f}% above max pain ₹{max_pain:.0f} — gravity pull down")
                    score -= 1
                else:
                    points.append(f"Price {dist_pct:.1f}% below max pain ₹{max_pain:.0f} — gravity pull up")
                    score += 1

        # ── Market breadth ────────────────────────────────────────────────
        if advance_decline_ratio > 2.0:
            score += 0.5
            points.append(f"A/D ratio {advance_decline_ratio:.1f} — broad advance")
        elif advance_decline_ratio < 0.5:
            score -= 0.5
            points.append(f"A/D ratio {advance_decline_ratio:.1f} — broad decline")

        # ── VIX fear/greed ────────────────────────────────────────────────
        if vix < 12:
            score += 1
            points.append("VIX very low — calm market, bulls in control")
        elif vix > 25:
            score -= 1.5
            points.append(f"VIX {vix:.1f} elevated — fear in market")

        # ── Nifty direction confirmation ──────────────────────────────────
        if nifty_change_pct > 0.5:
            score += 0.5
        elif nifty_change_pct < -0.5:
            score -= 0.5

        # Smart money score (0–100)
        result["smart_money_score"] = int(min(100, max(0, score * 10)))
        result["score"] = max(0, min(10, round(score)))

        if score >= 7:
            result["smart_money_bias"] = "STRONGLY_BULLISH"
        elif score >= 5.5:
            result["smart_money_bias"] = "BULLISH"
        elif score <= 3:
            result["smart_money_bias"] = "STRONGLY_BEARISH"
        elif score <= 4.5:
            result["smart_money_bias"] = "BEARISH"
        else:
            result["smart_money_bias"] = "NEUTRAL"

        result["description"] = (
            f"SM Score: {result['smart_money_score']}/100 | "
            f"Institutional: {result['institutional_flow']} | "
            f"Retail (PCR): {result['retail_sentiment']} | "
            f"{' | '.join(points[:3])}"
        )

        return result


sentiment_agent = SentimentAgent()

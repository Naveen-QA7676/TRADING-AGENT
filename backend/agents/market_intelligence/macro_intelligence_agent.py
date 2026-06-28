"""
Macro Intelligence Agent — Agent 2.
Analyzes FII/DII, VIX, PCR, options chain, and institutional flows.
"""

from loguru import logger


class MacroIntelligenceAgent:
    name = "Macro Intelligence Agent"

    def analyze(
        self,
        fii_dii: dict,
        vix: float,
        options_data: dict,
        market_breadth: dict | None = None,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "fii_net": 0,
            "dii_net": 0,
            "fii_bias": "NEUTRAL",
            "vix_level": vix,
            "vix_status": "NORMAL",
            "pcr": 1.0,
            "max_pain": 0,
            "pcr_bias": "NEUTRAL",
            "advance_decline": {},
            "description": "",
        }

        try:
            score = 5

            # FII/DII analysis
            fii_net = fii_dii.get("fii_net", 0)
            dii_net = fii_dii.get("dii_net", 0)
            result["fii_net"] = fii_net
            result["dii_net"] = dii_net

            if fii_net > 1000:
                score += 2
                result["fii_bias"] = "STRONG_BUY"
            elif fii_net > 500:
                score += 1
                result["fii_bias"] = "BUY"
            elif fii_net > 0:
                result["fii_bias"] = "MILD_BUY"
            elif fii_net < -1000:
                score -= 2
                result["fii_bias"] = "STRONG_SELL"
            elif fii_net < -500:
                score -= 1
                result["fii_bias"] = "SELL"
            else:
                result["fii_bias"] = "MILD_SELL"

            # VIX analysis
            if vix < 12:
                score += 1
                result["vix_status"] = "VERY_CALM"
            elif vix < 15:
                result["vix_status"] = "CALM"
            elif vix < 20:
                result["vix_status"] = "NORMAL"
            elif vix < 25:
                score -= 1
                result["vix_status"] = "ELEVATED"
            else:
                score -= 2
                result["vix_status"] = "HIGH"

            # PCR analysis
            pcr = options_data.get("pcr", 1.0)
            max_pain = options_data.get("max_pain", 0)
            result["pcr"] = pcr
            result["max_pain"] = max_pain

            if pcr > 1.2:
                score += 1
                result["pcr_bias"] = "BULLISH"
            elif pcr < 0.7:
                score -= 1
                result["pcr_bias"] = "BEARISH"
            else:
                result["pcr_bias"] = "NEUTRAL"

            # Market breadth
            if market_breadth:
                adv = market_breadth.get("advancing", 0)
                dec = market_breadth.get("declining", 0)
                result["advance_decline"] = market_breadth
                if adv > dec * 1.5:
                    score += 1
                elif dec > adv * 1.5:
                    score -= 1

            score = max(0, min(10, score))
            result["score"] = score

            desc_parts = [
                f"FII: {fii_net:+,.0f}Cr ({result['fii_bias']})",
                f"DII: {dii_net:+,.0f}Cr",
                f"VIX: {vix:.1f} ({result['vix_status']})",
                f"PCR: {pcr:.2f} ({result['pcr_bias']})",
                f"Max Pain: {max_pain}",
            ]
            result["description"] = " | ".join(desc_parts)

        except Exception as e:
            logger.error(f"Macro Intelligence Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


macro_intelligence_agent = MacroIntelligenceAgent()

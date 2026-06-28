"""
Global Correlation Agent — Agent 6.
Analyzes US markets, DXY, crude, gold, and bond yields for India impact.
"""

from loguru import logger


class GlobalCorrelationAgent:
    name = "Global Correlation Agent"

    def analyze(self, global_data: dict) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "global_bias": "NEUTRAL",
            "key_factors": [],
            "risk_off": False,
            "description": "",
        }

        if not global_data:
            result["description"] = "No global data available"
            return result

        try:
            score = 5
            factors = []

            sp500 = global_data.get("sp500", {})
            sp_chg = sp500.get("change_pct", 0)
            if sp_chg > 1:
                score += 2
                factors.append(f"S&P 500 +{sp_chg:.1f}% — VERY POSITIVE for India")
            elif sp_chg > 0.3:
                score += 1
                factors.append(f"S&P 500 +{sp_chg:.1f}% — positive for India")
            elif sp_chg < -1:
                score -= 2
                factors.append(f"S&P 500 {sp_chg:.1f}% — NEGATIVE for India")
            elif sp_chg < -0.3:
                score -= 1
                factors.append(f"S&P 500 {sp_chg:.1f}% — mild negative")

            vix_us = global_data.get("vix_us", {})
            vix_val = vix_us.get("price", 18)
            if vix_val > 30:
                score -= 3
                result["risk_off"] = True
                factors.append(f"VIX {vix_val:.0f} — RISK OFF! Avoid aggressive trades")
            elif vix_val > 20:
                score -= 1
                factors.append(f"VIX {vix_val:.0f} — elevated, caution")
            elif vix_val < 13:
                score += 1
                factors.append(f"VIX {vix_val:.0f} — very calm, risk on")

            dxy = global_data.get("dxy", {})
            dxy_chg = dxy.get("change_pct", 0)
            if dxy_chg > 0.5:
                score -= 1
                factors.append(f"DXY +{dxy_chg:.2f}% — USD strong, FII pressure on India")
            elif dxy_chg < -0.5:
                score += 1
                factors.append(f"DXY {dxy_chg:.2f}% — USD weak, EM currencies benefit")

            crude = global_data.get("crude_wti", {})
            crude_chg = crude.get("change_pct", 0)
            if crude_chg > 3:
                score -= 1
                factors.append(f"Crude +{crude_chg:.1f}% — inflation risk for India")
            elif crude_chg < -3:
                score += 1
                factors.append(f"Crude {crude_chg:.1f}% — positive for India")

            nikkei = global_data.get("nikkei", {})
            nikkei_chg = nikkei.get("change_pct", 0)
            if nikkei_chg > 1:
                score += 0.5
                factors.append(f"Nikkei +{nikkei_chg:.1f}% — Asian markets positive")
            elif nikkei_chg < -1:
                score -= 0.5
                factors.append(f"Nikkei {nikkei_chg:.1f}% — Asian weakness")

            # Determine global bias
            score = max(0, min(10, score))
            if score >= 7:
                result["global_bias"] = "BULLISH"
            elif score <= 3:
                result["global_bias"] = "BEARISH"
            else:
                result["global_bias"] = "NEUTRAL"

            result.update({
                "score": int(score),
                "key_factors": factors[:5],
                "description": f"Global: {result['global_bias']} | " + " | ".join(factors[:3]),
            })

        except Exception as e:
            logger.error(f"Global Correlation Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


global_correlation_agent = GlobalCorrelationAgent()

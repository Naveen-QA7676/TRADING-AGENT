"""
Options Analysis Agent — Agent 10.
Analyzes Nifty/BankNifty options chain for:
- Put-Call Ratio (PCR)
- Max Pain level
- IV Percentile
- Gamma walls (high OI strikes)
- Implied move for the day
"""

from loguru import logger
from backend.web_research.nse_scraper import nse_scraper


class OptionsAnalysisAgent:
    name = "Options Analysis Agent"

    async def analyze(
        self,
        index_symbol: str,
        ltp: float,
        expiry_dte: int = 0,
    ) -> dict:
        result = {
            "agent": self.name,
            "score": 5,
            "pcr": 0.0,
            "max_pain": 0.0,
            "put_oi": 0,
            "call_oi": 0,
            "top_call_strikes": [],
            "top_put_strikes": [],
            "gamma_wall_above": 0.0,
            "gamma_wall_below": 0.0,
            "implied_move_pct": 0.0,
            "iv_environment": "NORMAL",
            "bias": "NEUTRAL",
            "description": "",
        }

        try:
            chain = await nse_scraper.get_options_chain(index_symbol)
            if not chain:
                result["description"] = "Options chain unavailable"
                return result

            pcr = chain.get("pcr", 1.0)
            max_pain = chain.get("max_pain", ltp)
            put_oi = chain.get("total_put_oi", 0)
            call_oi = chain.get("total_call_oi", 0)
            strikes = chain.get("strikes", [])

            result["pcr"] = round(pcr, 3)
            result["max_pain"] = max_pain
            result["put_oi"] = put_oi
            result["call_oi"] = call_oi

            # Find gamma walls: strikes with highest OI
            if strikes:
                sorted_calls = sorted(strikes, key=lambda x: x.get("call_oi", 0), reverse=True)
                sorted_puts = sorted(strikes, key=lambda x: x.get("put_oi", 0), reverse=True)

                result["top_call_strikes"] = [
                    {"strike": s["strike"], "oi": s["call_oi"]}
                    for s in sorted_calls[:3] if s["strike"] > ltp
                ]
                result["top_put_strikes"] = [
                    {"strike": s["strike"], "oi": s["put_oi"]}
                    for s in sorted_puts[:3] if s["strike"] < ltp
                ]

                if result["top_call_strikes"]:
                    result["gamma_wall_above"] = result["top_call_strikes"][0]["strike"]
                if result["top_put_strikes"]:
                    result["gamma_wall_below"] = result["top_put_strikes"][0]["strike"]

            # Implied move estimation from ATM straddle price
            atm_iv = chain.get("atm_iv", 0)
            if atm_iv and expiry_dte >= 0:
                dte = max(1, expiry_dte)
                result["implied_move_pct"] = round(atm_iv * (dte ** 0.5) / (252 ** 0.5), 2)

            # IV environment
            iv_percentile = chain.get("iv_percentile", 50)
            if iv_percentile > 75:
                result["iv_environment"] = "HIGH_IV"
            elif iv_percentile < 25:
                result["iv_environment"] = "LOW_IV"
            else:
                result["iv_environment"] = "NORMAL"

            # Score and bias
            score = 5
            if pcr > 1.2:
                score += 1.5
                result["bias"] = "BULLISH"
            elif pcr > 1.0:
                score += 0.5
                result["bias"] = "MILDLY_BULLISH"
            elif pcr < 0.7:
                score -= 1.5
                result["bias"] = "BEARISH"
            elif pcr < 0.9:
                score -= 0.5
                result["bias"] = "MILDLY_BEARISH"

            # Price near max pain → magnetic pull
            mp_dist = (ltp - max_pain) / ltp * 100
            if abs(mp_dist) < 0.5:
                result["at_max_pain"] = True
                score += 0.5
            elif mp_dist > 1.5:
                score -= 0.5  # stretched above max pain, gravity pull down

            # Gamma wall proximity
            if result["gamma_wall_above"] > 0:
                dist_above = (result["gamma_wall_above"] - ltp) / ltp * 100
                if dist_above < 0.5:
                    result["near_call_wall"] = True
                    result["description_hint"] = f"Heavy call OI at {result['gamma_wall_above']} — possible resistance"
                    score -= 0.5

            result["score"] = max(0, min(10, round(score)))
            result["description"] = (
                f"PCR: {pcr:.2f} | Max Pain: ₹{max_pain:.0f} | "
                f"Gamma Wall ↑{result['gamma_wall_above']:.0f} ↓{result['gamma_wall_below']:.0f} | "
                f"IV: {result['iv_environment']} | Bias: {result['bias']}"
            )

        except Exception as e:
            logger.error(f"Options Analysis Agent error: {e}")
            result["description"] = f"Error: {str(e)}"

        return result


options_analysis_agent = OptionsAnalysisAgent()

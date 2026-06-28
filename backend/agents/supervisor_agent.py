"""
Supervisor Agent — the master brain that synthesizes all 20 specialist agents
into one final trade recommendation using Claude claude-opus-4-8.
5-stage sequential prompt pipeline for maximum accuracy.
"""

import json
import time
from dataclasses import dataclass, field
from loguru import logger

import anthropic

from backend.config import settings
from backend.knowledge.supervisor_prompt import SUPERVISOR_SYSTEM_PROMPT


@dataclass
class SupervisorInput:
    """All data collected by specialist agents, fed to Supervisor."""
    symbol: str
    ltp: float
    market_regime: str
    market_structure: dict
    macro_context: dict
    news_context: dict
    sector_context: dict
    global_context: dict
    sentiment_context: dict
    order_flow: dict
    volume_profile: dict
    microstructure: dict
    technical_5m: dict
    technical_15m: dict
    technical_1h: dict
    technical_daily: dict
    strategy_candidates: list[dict]
    options_data: dict
    risk_data: dict
    portfolio_state: dict
    historical_edge: dict
    capital: float = 150000.0


@dataclass
class SupervisorOutput:
    suggestion: dict | None      # full trade suggestion or None
    confidence_score: int
    no_suggestion_reason: str = ""
    processing_time_ms: int = 0
    stage_outputs: list[dict] = field(default_factory=list)


class SupervisorAgent:
    """
    5-stage Claude prompt pipeline:
    Stage 1: Macro + Regime analysis
    Stage 2: Technical + Order Flow synthesis
    Stage 3: Strategy selection + Entry/Exit definition
    Stage 4: Risk + Position sizing
    Stage 5: Final synthesis → JSON output
    """

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = "claude-opus-4-8"

    def _call_claude(self, system: str, user: str, max_tokens: int = 2000) -> str:
        """Single Claude API call with retry logic."""
        from tenacity import retry, stop_after_attempt, wait_exponential
        for attempt in range(3):
            try:
                msg = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return msg.content[0].text
            except Exception as e:
                logger.warning(f"Claude API attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        return ""

    def _build_market_context_prompt(self, inp: SupervisorInput) -> str:
        return f"""
MARKET CONTEXT FOR SUPERVISOR ANALYSIS
Symbol: {inp.symbol} @ ₹{inp.ltp:.2f}
Market Regime: {inp.market_regime}
Market Structure: {json.dumps(inp.market_structure, indent=2)}
Global Context: {json.dumps(inp.global_context, indent=2)}
Macro Context: {json.dumps(inp.macro_context, indent=2)}
Sector Context: {json.dumps(inp.sector_context, indent=2)}
News Context: {json.dumps(inp.news_context, indent=2)}
Options Data: {json.dumps(inp.options_data, indent=2)}
"""

    def _build_technical_prompt(self, inp: SupervisorInput) -> str:
        return f"""
TECHNICAL ANALYSIS SUMMARY FOR {inp.symbol}
5m Indicators: {json.dumps(inp.technical_5m, indent=2)}
15m Indicators: {json.dumps(inp.technical_15m, indent=2)}
1H Indicators: {json.dumps(inp.technical_1h, indent=2)}
Daily Indicators: {json.dumps(inp.technical_daily, indent=2)}
Order Flow: {json.dumps(inp.order_flow, indent=2)}
Volume Profile: {json.dumps(inp.volume_profile, indent=2)}
Microstructure: {json.dumps(inp.microstructure, indent=2)}
"""

    def analyze(self, inp: SupervisorInput) -> SupervisorOutput:
        """Run the 5-stage analysis pipeline."""
        start = time.time()
        stage_outputs = []
        output = SupervisorOutput(suggestion=None, confidence_score=0)

        try:
            # ── STAGE 1: Macro & Regime ──────────────────────────────────────
            stage1_prompt = f"""
{self._build_market_context_prompt(inp)}

STAGE 1 TASK: Analyze the macro and regime context.
Answer these questions concisely:
1. Is the overall market environment conducive to trading {inp.symbol} today?
2. What is the macro bias (bullish/bearish/neutral) and why?
3. What sector rank does this stock hold today?
4. Are there any macro red flags that should PREVENT trading?

Score the macro environment: 0-10 (10 = perfect conditions for this trade)
"""
            stage1 = self._call_claude(SUPERVISOR_SYSTEM_PROMPT, stage1_prompt, 800)
            stage_outputs.append({"stage": 1, "title": "Macro & Regime", "output": stage1})
            logger.debug(f"Stage 1 complete for {inp.symbol}")

            # ── STAGE 2: Technical + Order Flow ─────────────────────────────
            stage2_prompt = f"""
{self._build_technical_prompt(inp)}
Strategy candidates identified: {json.dumps(inp.strategy_candidates, indent=2)}

STAGE 2 TASK: Synthesize all technical and order flow data.
1. Are the technical indicators aligned across timeframes (5m/15m/1H)?
2. Is order flow (CVD, delta) confirming the technical direction?
3. What is the Volume Profile saying (price at POC/VAH/VAL/HVN/LVN)?
4. Which strategy from the candidates is most appropriate and why?

Score technical alignment: 0-10
"""
            stage2 = self._call_claude(SUPERVISOR_SYSTEM_PROMPT, stage2_prompt, 800)
            stage_outputs.append({"stage": 2, "title": "Technical + Order Flow", "output": stage2})
            logger.debug(f"Stage 2 complete for {inp.symbol}")

            # ── STAGE 3: Strategy Selection ──────────────────────────────────
            stage3_prompt = f"""
STAGE 3 TASK: Define the exact trade setup.
Based on stages 1 and 2:
- Stage 1 output: {stage1}
- Stage 2 output: {stage2}

Current price: ₹{inp.ltp:.2f}
Capital: ₹{inp.capital:,.0f}

Determine:
1. Should we suggest a trade? (YES / NO with reason)
2. If YES: Entry zone, Stop Loss, Target 1, Target 2, Invalidation level
3. List the top 5 reasons FOR this trade
4. List the top 3 reasons AGAINST
5. What would invalidate this setup?
6. Confidence score: 0-100

IMPORTANT: If this is a HIGH CONVICTION setup (>80), clearly say so.
If confidence < 70, say NO TRADE with specific reason.
"""
            stage3 = self._call_claude(SUPERVISOR_SYSTEM_PROMPT, stage3_prompt, 1000)
            stage_outputs.append({"stage": 3, "title": "Strategy Selection", "output": stage3})
            logger.debug(f"Stage 3 complete for {inp.symbol}")

            # ── STAGE 4: Risk + Position Sizing ─────────────────────────────
            stage4_prompt = f"""
STAGE 4 TASK: Risk management and position sizing.
Trade setup from stage 3: {stage3}
Risk data: {json.dumps(inp.risk_data, indent=2)}
Portfolio state: {json.dumps(inp.portfolio_state, indent=2)}
Historical edge: {json.dumps(inp.historical_edge, indent=2)}

Calculate:
1. Position size (1% risk rule: qty = (capital × 0.01) / (entry - SL))
2. Win probability based on setup quality and historical edge
3. 3-scenario probabilities: WIN / STOP HIT / SIDEWAYS
4. Adjusted R:R ratio
5. Any risk flags that should reduce position size or cancel trade

Capital: ₹{inp.capital:,.0f}
Max risk per trade: 1% = ₹{inp.capital * 0.01:,.0f}
"""
            stage4 = self._call_claude(SUPERVISOR_SYSTEM_PROMPT, stage4_prompt, 800)
            stage_outputs.append({"stage": 4, "title": "Risk + Position Sizing", "output": stage4})
            logger.debug(f"Stage 4 complete for {inp.symbol}")

            # ── STAGE 5: Final JSON Output ───────────────────────────────────
            stage5_prompt = f"""
STAGE 5: Generate the final trade suggestion as valid JSON.

Summary from all stages:
Stage 1 (Macro): {stage1[:300]}...
Stage 2 (Technical): {stage2[:300]}...
Stage 3 (Setup): {stage3[:500]}...
Stage 4 (Risk): {stage4[:400]}...

Agent scores (from specialist agents):
{json.dumps({
    k: v for k, v in inp.market_structure.items()
    if k in ["score", "regime", "structure"]
}, indent=2)}

Now generate the FINAL output as JSON following EXACTLY the output format in your system prompt.
If suggesting a trade: output the full trade suggestion JSON.
If NOT suggesting: output {{"no_suggestion": true, "reason": "...", "what_would_change_it": "..."}}

CRITICAL: Output ONLY valid JSON. No markdown, no explanation outside the JSON.
"""
            stage5 = self._call_claude(SUPERVISOR_SYSTEM_PROMPT, stage5_prompt, 1500)
            stage_outputs.append({"stage": 5, "title": "Final JSON", "output": stage5})

            # Parse JSON output
            try:
                # Extract JSON from response
                json_str = stage5.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()

                result = json.loads(json_str)

                if result.get("no_suggestion"):
                    output.suggestion = None
                    output.confidence_score = 0
                    output.no_suggestion_reason = result.get("reason", "No valid setup")
                else:
                    output.suggestion = result
                    output.confidence_score = result.get("confidence_score", 0)

            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error from Claude output: {e}\nOutput: {stage5[:200]}")
                output.no_suggestion_reason = "JSON parse error in supervisor output"

        except Exception as e:
            logger.error(f"Supervisor analysis failed for {inp.symbol}: {e}")
            output.no_suggestion_reason = f"Supervisor error: {str(e)}"

        output.processing_time_ms = int((time.time() - start) * 1000)
        output.stage_outputs = stage_outputs
        logger.info(f"Supervisor complete for {inp.symbol}: score={output.confidence_score}, time={output.processing_time_ms}ms")
        return output


supervisor_agent = SupervisorAgent()

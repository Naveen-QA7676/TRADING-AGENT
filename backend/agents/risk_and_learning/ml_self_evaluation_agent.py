"""
ML Self-Evaluation Agent — Agent 20.
Runs every Saturday to evaluate system performance.
Identifies which setups are working, which agents are under-scoring, and what to improve.
Uses Claude to generate a human-readable weekly improvement report.
"""

import json
from loguru import logger
from anthropic import Anthropic
from backend.config import settings
from backend.agents.risk_and_learning.performance_analytics import performance_analytics


client = Anthropic(api_key=settings.anthropic_api_key)


class MLSelfEvaluationAgent:
    name = "ML Self-Evaluation Agent"

    async def weekly_review(self, trades: list[dict], agent_logs: list[dict]) -> dict:
        """
        Runs every Saturday at market close.
        Analyzes the week's trades to produce improvement recommendations.
        """
        result = {
            "agent": self.name,
            "week_stats": {},
            "top_performing_setup": "",
            "worst_performing_setup": "",
            "agent_accuracy_scores": {},
            "improvement_suggestions": [],
            "confidence_calibration": {},
            "report": "",
        }

        if len(trades) < 3:
            result["report"] = "Insufficient trades this week for meaningful analysis."
            return result

        try:
            # Compute performance stats
            stats = performance_analytics.compute_from_trades(trades)

            result["week_stats"] = {
                "total_trades": stats.total_trades,
                "win_rate": round(stats.win_rate, 3),
                "expectancy": round(stats.expectancy, 2),
                "profit_factor": round(stats.profit_factor, 2),
                "sharpe_ratio": round(stats.sharpe_ratio, 2),
                "max_drawdown": round(stats.max_drawdown, 2),
                "best_setup": stats.best_setup,
                "worst_setup": stats.worst_setup,
                "best_time": stats.best_time,
            }
            result["top_performing_setup"] = stats.best_setup
            result["worst_performing_setup"] = stats.worst_setup

            # Agent accuracy: compare predicted confidence vs actual outcome
            agent_accuracy = self._evaluate_agent_accuracy(trades, agent_logs)
            result["agent_accuracy_scores"] = agent_accuracy

            # Confidence calibration: was 80+ confidence actually ~80% win rate?
            calibration = self._calibrate_confidence(trades)
            result["confidence_calibration"] = calibration

            # Generate Claude report
            report_prompt = f"""
You are an AI trading system performing a weekly self-evaluation.

This week's performance data:
{json.dumps(result['week_stats'], indent=2)}

Agent accuracy scores (how well each agent's score predicted outcomes):
{json.dumps(agent_accuracy, indent=2)}

Confidence calibration (predicted confidence vs actual win rate by bucket):
{json.dumps(calibration, indent=2)}

By setup performance:
{json.dumps(stats.by_setup, indent=2)}

By time of day:
{json.dumps(stats.by_hour, indent=2)}

Generate a concise weekly improvement report covering:
1. What worked well this week (be specific about setups and conditions)
2. What failed and why (pattern in losing trades)
3. Agent calibration issues (which agents are over/under-scoring)
4. Specific actionable suggestions for next week
5. Confidence threshold adjustment recommendation (currently 70 — should it change?)

Be concrete and specific. No generic advice.
"""

            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=1500,
                messages=[{"role": "user", "content": report_prompt}],
            )

            result["report"] = response.content[0].text
            result["improvement_suggestions"] = self._extract_suggestions(result["report"])

        except Exception as e:
            logger.error(f"ML Self-Evaluation Agent error: {e}")
            result["report"] = f"Error generating report: {str(e)}"

        return result

    def _evaluate_agent_accuracy(self, trades: list[dict], agent_logs: list[dict]) -> dict:
        """For each agent, check: when score was high (>=7), was outcome a win?"""
        accuracy: dict[str, dict] = {}

        for trade in trades:
            suggestion_id = trade.get("suggestion_id")
            outcome = "WIN" if (trade.get("r_multiple") or 0) > 0 else "LOSS"

            matching_log = next(
                (l for l in agent_logs if l.get("suggestion_id") == suggestion_id), None
            )
            if not matching_log:
                continue

            agent_scores = matching_log.get("agent_scores", {})
            for agent_name, score in agent_scores.items():
                if agent_name not in accuracy:
                    accuracy[agent_name] = {"high_score_wins": 0, "high_score_losses": 0, "total": 0}
                accuracy[agent_name]["total"] += 1
                if score >= 7:
                    if outcome == "WIN":
                        accuracy[agent_name]["high_score_wins"] += 1
                    else:
                        accuracy[agent_name]["high_score_losses"] += 1

        for agent, data in accuracy.items():
            total_high = data["high_score_wins"] + data["high_score_losses"]
            data["high_score_accuracy"] = round(
                data["high_score_wins"] / total_high, 3
            ) if total_high > 0 else 0.5

        return accuracy

    def _calibrate_confidence(self, trades: list[dict]) -> dict:
        """Group trades by confidence bucket, check actual win rate."""
        buckets: dict[str, dict] = {
            "70-75": {"wins": 0, "total": 0},
            "76-80": {"wins": 0, "total": 0},
            "81-85": {"wins": 0, "total": 0},
            "86-90": {"wins": 0, "total": 0},
            "91+":   {"wins": 0, "total": 0},
        }
        for t in trades:
            conf = t.get("confidence_score", 70)
            r = t.get("r_multiple", 0) or 0
            if conf < 76:
                key = "70-75"
            elif conf < 81:
                key = "76-80"
            elif conf < 86:
                key = "81-85"
            elif conf < 91:
                key = "86-90"
            else:
                key = "91+"
            buckets[key]["total"] += 1
            if r > 0:
                buckets[key]["wins"] += 1

        for key, data in buckets.items():
            data["win_rate"] = round(data["wins"] / data["total"], 3) if data["total"] > 0 else 0.0

        return buckets

    def _extract_suggestions(self, report: str) -> list[str]:
        """Extract bullet points from Claude's report."""
        lines = report.split("\n")
        suggestions = [
            line.strip().lstrip("•-123456789. ")
            for line in lines
            if line.strip().startswith(("•", "-", "1.", "2.", "3.", "4.", "5."))
        ]
        return suggestions[:10]


ml_self_evaluation_agent = MLSelfEvaluationAgent()

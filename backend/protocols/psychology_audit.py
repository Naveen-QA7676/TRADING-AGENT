"""
Psychology Audit — detects emotional bias patterns in trading behavior.
Runs analysis on recent trade history to catch revenge trading,
overtrading, fear of missing out, and loss aversion.
"""

from datetime import datetime, timedelta
from loguru import logger


class PsychologyAudit:
    """
    Analyzes trade patterns for emotional bias.
    Called: (1) Before every suggestion cycle, (2) After a loss, (3) Weekly review.
    """

    def audit(
        self,
        trades_today: list[dict],
        trades_week: list[dict],
        daily_pnl: float,
        capital: float,
    ) -> dict:
        result = {
            "flags": [],
            "risk_level": "LOW",
            "recommendation": "PROCEED",
            "score_penalty": 0,
            "description": "",
        }

        flags = []
        penalty = 0

        # ── Revenge trading ────────────────────────────────────────────────
        # Pattern: loss followed immediately by another trade within 10 minutes
        for i in range(1, len(trades_today)):
            prev = trades_today[i - 1]
            curr = trades_today[i]
            prev_r = prev.get("r_multiple", 0) or 0
            if prev_r < 0:
                prev_exit = prev.get("exit_time")
                curr_entry = curr.get("entry_time")
                if isinstance(prev_exit, datetime) and isinstance(curr_entry, datetime):
                    gap = (curr_entry - prev_exit).total_seconds() / 60
                    if gap < 10:
                        flags.append(
                            f"REVENGE TRADE DETECTED: Entered {curr.get('symbol')} "
                            f"only {gap:.0f}m after a loss on {prev.get('symbol')}. "
                            "Revenge trades statistically lose money."
                        )
                        penalty += 3

        # ── Overtrading ────────────────────────────────────────────────────
        if len(trades_today) >= 5:
            flags.append(
                f"OVERTRADING: {len(trades_today)} trades today. "
                "Quality > quantity. More trades = more slippage + emotional decisions."
            )
            penalty += 2

        # ── Loss aversion / cutting winners early ─────────────────────────
        if trades_week:
            avg_win_r = 0
            avg_loss_r = 0
            wins = [t for t in trades_week if (t.get("r_multiple") or 0) > 0]
            losses = [t for t in trades_week if (t.get("r_multiple") or 0) < 0]

            if wins:
                avg_win_r = sum(t["r_multiple"] for t in wins) / len(wins)
            if losses:
                avg_loss_r = abs(sum(t["r_multiple"] for t in losses) / len(losses))

            if avg_win_r < 0.8 and len(wins) >= 3:
                flags.append(
                    f"CUTTING WINNERS EARLY: Avg win = {avg_win_r:.1f}R (below 1R). "
                    "You're exiting before targets. Trust your plan."
                )
                penalty += 1

            if avg_loss_r > 1.5 and len(losses) >= 3:
                flags.append(
                    f"NOT RESPECTING STOPS: Avg loss = {avg_loss_r:.1f}R (above 1R). "
                    "Stop losses being moved or ignored."
                )
                penalty += 3

        # ── FOMO check ─────────────────────────────────────────────────────
        if trades_today:
            low_confidence = [
                t for t in trades_today
                if (t.get("confidence_score") or 100) < 70
            ]
            if low_confidence:
                flags.append(
                    f"FOMO: {len(low_confidence)} trade(s) taken below 70 confidence. "
                    "The system's min threshold exists for a reason."
                )
                penalty += 2

        # ── Large loss today → emotional state ────────────────────────────
        loss_pct = abs(daily_pnl) / capital * 100 if capital else 0
        if daily_pnl < 0 and loss_pct > 1.5:
            flags.append(
                f"LARGE LOSS DAY: Down {loss_pct:.1f}% today. "
                "Research shows performance degrades after a significant loss. "
                "Consider stopping for the day."
            )
            penalty += 2

        # ── Consecutive losses ─────────────────────────────────────────────
        if len(trades_today) >= 2:
            last_n = trades_today[-3:]
            if all((t.get("r_multiple") or 0) < 0 for t in last_n):
                flags.append(
                    f"3 CONSECUTIVE LOSSES: Consider a mandatory 30-min break. "
                    "The market is currently not aligned with your edge."
                )
                penalty += 2

        # Final risk level
        if penalty >= 6:
            result["risk_level"] = "CRITICAL"
            result["recommendation"] = "STOP_TRADING"
        elif penalty >= 3:
            result["risk_level"] = "HIGH"
            result["recommendation"] = "REDUCE_SIZE"
        elif penalty >= 1:
            result["risk_level"] = "MEDIUM"
            result["recommendation"] = "PROCEED_WITH_CAUTION"
        else:
            result["risk_level"] = "LOW"
            result["recommendation"] = "PROCEED"

        result["flags"] = flags
        result["score_penalty"] = penalty
        result["description"] = (
            f"Psychology Risk: {result['risk_level']} | "
            f"{len(flags)} flags | "
            f"Recommendation: {result['recommendation']}"
        )

        if flags:
            logger.warning(f"Psychology audit flags: {flags}")

        return result


psychology_audit = PsychologyAudit()

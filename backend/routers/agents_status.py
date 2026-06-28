from fastapi import APIRouter
from datetime import datetime, timezone
from typing import Literal

router = APIRouter(tags=["agents"])

AgentStatusLiteral = Literal["ACTIVE", "WAITING", "SLEEP", "ERROR"]

AGENT_NAMES = [
    # Market Intelligence
    "market_regime_agent", "multi_tf_agent", "market_structure_agent",
    "vwap_agent", "momentum_agent", "volume_profile_agent", "global_macro_agent",
    # Execution Intelligence
    "entry_timing_agent", "stop_loss_agent", "target_agent",
    "position_sizing_agent", "risk_reward_agent", "pattern_recognition_agent",
    "orb_agent", "fii_dii_agent",
    # Risk & Learning
    "portfolio_risk_agent", "news_sentiment_agent", "historical_edge_agent",
    "learning_agent", "regime_strategy_mapper",
    # Supervisor
    "supervisor_agent",
]

# In-memory agent state (updated when agents run in the pipeline)
_agent_registry: dict[str, dict] = {
    name: {
        "name": name,
        "status": "WAITING",
        "last_run": None,
        "last_output": None,
        "run_count": 0,
        "error_count": 0,
    }
    for name in AGENT_NAMES
}


def update_agent(name: str, status: AgentStatusLiteral, output: str | None = None) -> None:
    """Called by agent pipeline to push status updates."""
    if name not in _agent_registry:
        _agent_registry[name] = {"name": name, "run_count": 0, "error_count": 0}
    entry = _agent_registry[name]
    entry["status"] = status
    entry["last_run"] = datetime.now(timezone.utc).isoformat()
    if output is not None:
        entry["last_output"] = output
    if status == "ACTIVE":
        entry["run_count"] = entry.get("run_count", 0) + 1
    if status == "ERROR":
        entry["error_count"] = entry.get("error_count", 0) + 1


@router.get("/")
async def get_agents_status():
    return list(_agent_registry.values())


@router.get("/{agent_name}")
async def get_agent_status(agent_name: str):
    if agent_name not in _agent_registry:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return _agent_registry[agent_name]

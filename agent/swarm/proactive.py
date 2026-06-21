"""Proactive heartbeat-driven autonomous swarms."""
import logging

from agent import store
from agent.swarm.runner import run_swarm
from agent.swarm.topology import route_topology
from config import config

logger = logging.getLogger(__name__)


async def run_proactive_swarm(context: str = "") -> dict:
    """Budget-aware swarm triggered by heartbeat or scheduler."""
    if not getattr(config, "swarm_enabled", True):
        return {"skipped": True, "reason": "swarm disabled"}

    # Budget check
    cap = getattr(config, "daily_llm_call_cap", 0)
    if cap > 0:
        usage = store.usage_today()
        if usage.get("llm_calls", 0) >= cap * 0.8:
            return {"skipped": True, "reason": "approaching daily LLM cap"}

    goals = store.list_goals(status="active")[:3]
    if not goals:
        return {"skipped": True, "reason": "no active goals"}

    results = []
    for g in goals:
        goal_text = f"{g['title']}: {g.get('detail', '')}"
        ctx = f"{context}\n\nActive goal priority: {g.get('priority', 3)}" if context else ""
        steps = [{"description": f"Advance goal: {goal_text}", "depends_on": [], "specialist": "ops"}]
        if "research" in goal_text.lower() or "find" in goal_text.lower():
            steps.append({"description": f"Research for: {goal_text}", "depends_on": [0], "specialist": "researcher"})

        topo = route_topology(goal_text, steps)
        r = await run_swarm(f"{goal_text}\n{ctx}", steps=steps, topology=topo.value)
        results.append({"goal_id": g["id"], "goal": goal_text, "result": r})

    return {"goals_processed": len(results), "results": results}

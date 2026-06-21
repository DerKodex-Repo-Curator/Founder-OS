"""Self-evolving swarm — integrates skills_factory for runtime tool creation."""
import logging

from agent import store, skills_factory
from agent.swarm.runner import run_swarm
from agent.swarm.profiles import reinforce_profile
from config import config

logger = logging.getLogger(__name__)


async def run_evolve_swarm(goal: str, propose_skill: bool = True) -> dict:
    """Run a swarm that can propose new skills/tools based on repeated patterns."""
    steps = [
        {"description": f"Analyze workflow for: {goal}", "specialist": "analyst", "depends_on": []},
        {"description": f"Execute core work: {goal}", "specialist": "researcher", "depends_on": [0]},
        {"description": f"Validate and summarize: {goal}", "specialist": "analyst", "depends_on": [1]},
    ]
    swarm_result = await run_swarm(goal, steps=steps, topology="sequential")

    skill_proposal = None
    if propose_skill and getattr(config, "swarm_enabled", True):
        # Check if a similar skill already exists
        existing = store.list_skills()
        names = {s["name"] for s in existing}
        suggested_name = goal.lower().replace(" ", "_")[:30]
        if suggested_name not in names and len(goal) > 20:
            skill_proposal = {
                "name": suggested_name,
                "when_to_use": f"When the founder asks to: {goal[:200]}",
                "steps": swarm_result.get("synthesis", "")[:500],
                "note": "Proposed by evolve swarm — use propose_skill or create_tool to formalize.",
            }
            store.upsert_skill(
                f"swarm_{suggested_name[:20]}",
                skill_proposal["when_to_use"],
                skill_proposal["steps"],
            )

    reinforce_profile("analyst", bool(swarm_result.get("synthesis")), delta=0.15)

    return {
        "goal": goal,
        "swarm_result": swarm_result,
        "skill_proposal": skill_proposal,
        "generated_tools_loaded": skills_factory.load_generated(),
    }

"""Mesh coordination — agents iterate on a shared artifact until convergence."""
import logging

from agent import subagent, critic, store
from config import config

logger = logging.getLogger(__name__)

_MESH_ROLES = [
    ("writer", "Improve and expand the artifact. Be clear and actionable."),
    ("editor", "Polish structure, tone, and clarity. Cut redundancy."),
    ("fact_checker", "Verify claims, flag unsupported statements, suggest fixes."),
]


async def run_mesh(artifact: str, goal: str, agents: int = 4, max_rounds: int = 5,
                   convergence_threshold: float = 0.85) -> dict:
    """3-8 agents iterate on a shared artifact until quality converges."""
    agents = min(max(3, agents), 8)
    max_rounds = min(max_rounds, getattr(config, "swarm_max_rounds", 10))
    current = artifact
    history = []
    prev_score = 0.0

    for rnd in range(max_rounds):
        round_edits = []
        for idx in range(agents):
            role_name, role_brief = _MESH_ROLES[idx % len(_MESH_ROLES)]
            task = (
                f"{role_brief}\n\nGOAL: {goal}\n\nCURRENT ARTIFACT:\n{current[:3000]}\n\n"
                f"Round {rnd + 1}. Return the improved artifact only."
            )
            spec = "analyst" if role_name == "fact_checker" else "outreach" if role_name == "editor" else "researcher"
            r = await subagent.run_subagent(spec, task)
            edited = r.get("result", current)
            round_edits.append({"role": role_name, "output": edited[:500]})
            current = edited  # each agent builds on previous in round

        # Score with critic
        verification = await critic.verify_answer(goal, current, f"Mesh round {rnd + 1}")
        conf_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
        score = conf_map.get(verification.get("confidence", "medium"), 0.6)
        history.append({"round": rnd + 1, "edits": round_edits, "score": score, "verification": verification})

        if verification.get("ok") and score >= convergence_threshold:
            break
        if score <= prev_score and rnd > 0:
            break  # no improvement
        prev_score = score

    run_id = store.create_swarm_run(goal[:300], "mesh", agents)
    store.finish_swarm_run(run_id, "done", current[:4000])
    return {
        "run_id": run_id,
        "artifact": current,
        "rounds": len(history),
        "converged": history[-1]["score"] >= convergence_threshold if history else False,
        "history": history,
    }

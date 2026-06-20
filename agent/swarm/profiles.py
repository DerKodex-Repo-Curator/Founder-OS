"""Bio-inspired SwarmSys profiles — explorer/worker/validator + pheromone reinforcement."""
import logging

from agent import subagent, store
from config import config

logger = logging.getLogger(__name__)

ROLES = ("explorer", "worker", "validator")

_ROLE_BRIEFS = {
    "explorer": "You are an EXPLORER agent. Propose hypotheses, explore alternatives, cast a wide net.",
    "worker": "You are a WORKER agent. Execute subtasks precisely, refine details, produce deliverables.",
    "validator": "You are a VALIDATOR agent. Check consistency, accuracy, and completeness. Score 0-1.",
}


def _embed_text(text: str):
    try:
        from chromadb.utils import embedding_functions
        emb = embedding_functions.DefaultEmbeddingFunction()
        return emb([text])[0]
    except Exception:
        return None


def _cosine(a, b):
    try:
        import numpy as np
        a, b = np.asarray(a, dtype="float32"), np.asarray(b, dtype="float32")
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))
    except Exception:
        return 0.0


def list_profiles(role: str = None) -> list:
    return store.list_swarm_agents(role)


def reinforce_profile(agent_name: str, success: bool, delta: float = 0.1):
    """Pheromone reinforcement: strengthen validated traces, decay failures."""
    store.update_swarm_agent_pheromone(agent_name, success, delta)


async def assign_agent(task: str, role: str = "worker") -> dict:
    """Embedding-based task->agent matching with pheromone weighting."""
    profiles = store.list_swarm_agents(role)
    task_emb = _embed_text(task)

    if not profiles:
        # Bootstrap from specialists
        spec = {"explorer": "researcher", "worker": "ops", "validator": "analyst"}.get(role, "researcher")
        store.upsert_swarm_agent(spec, role, pheromone=1.0, specialty=task[:200])
        profiles = store.list_swarm_agents(role)

    best_name, best_score = None, -1.0
    for p in profiles:
        spec_emb = _embed_text(p.get("specialty", "") or p["name"])
        sim = _cosine(task_emb, spec_emb) if task_emb and spec_emb else 0.5
        score = sim * float(p.get("pheromone", 1.0))
        if score > best_score:
            best_score, best_name = score, p["name"]

    agent_name = best_name or subagent.list_specialists()[0]
    brief = _ROLE_BRIEFS.get(role, "")
    full_task = f"{brief}\n\nTASK:\n{task}"
    result = await subagent.run_subagent(agent_name, full_task)
    return {"agent": agent_name, "role": role, "match_score": best_score, "result": result}


async def run_swarmsys_cycle(task: str, cycles: int = 3) -> dict:
    """Full exploration-exploitation-validation cycle."""
    outputs = {}
    for role in ROLES:
        r = await assign_agent(task, role)
        outputs[role] = r

    # Validator scores drive pheromone update
    validator_result = outputs.get("validator", {}).get("result", {})
    val_text = validator_result.get("result", "") if isinstance(validator_result, dict) else str(validator_result)
    success = "1" in val_text[:50] or "valid" in val_text.lower() or "pass" in val_text.lower()
    for role in ("explorer", "worker"):
        agent = outputs.get(role, {}).get("agent")
        if agent:
            reinforce_profile(agent, success)

    return {"task": task, "cycles": cycles, "outputs": outputs, "pheromone_updated": success}

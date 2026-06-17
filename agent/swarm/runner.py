"""Swarm runner — DAG waves, fan-out/fan-in, result aggregation."""
import asyncio
import logging

from agent import subagent, store
from agent.swarm.topology import route_topology, topological_waves, Topology
from config import config
from llm.router import complete

logger = logging.getLogger(__name__)


def _cap_agents(n: int) -> int:
    return min(n, getattr(config, "swarm_max_agents", 5))


async def aggregate_results(goal: str, results: list, style: str = "synthesis") -> str:
    """Fan-in: merge parallel sub-agent outputs into one coherent answer."""
    if not results:
        return ""
    if len(results) == 1:
        r = results[0]
        return r.get("result", str(r)) if isinstance(r, dict) else str(r)

    parts = []
    for i, r in enumerate(results, 1):
        if isinstance(r, dict):
            spec = r.get("specialist", r.get("agent", "?"))
            body = r.get("result", r.get("output", str(r)))
            parts.append(f"[{spec}] {body}")
        else:
            parts.append(f"[{i}] {r}")

    messages = [
        {"role": "system", "content":
            "You synthesize multiple specialist sub-agent results into one clear, "
            "non-redundant answer for the founder. Preserve facts, resolve conflicts "
            "explicitly, and stay concise."},
        {"role": "user", "content": f"GOAL:\n{goal[:800]}\n\nSUB-RESULTS:\n" + "\n\n".join(parts)[:6000]},
    ]
    try:
        return await complete(messages, task_type="analysis", max_tokens=1200)
    except Exception as e:
        logger.debug(f"[swarm] aggregate fallback: {e}")
        return "\n\n".join(parts)


async def run_swarm(goal: str, steps: list = None, topology: str = "",
                    specialist_map: dict = None) -> dict:
    """Execute a swarm run with adaptive topology selection.

    `steps`: list of {description, depends_on[], specialist?}
    Returns {topology, waves_run, results, synthesis, run_id}.
    """
    if not getattr(config, "swarm_enabled", True):
        return {"error": "Swarm is disabled (SWARM_ENABLED=false)."}

    steps = steps or [{"description": goal, "depends_on": []}]
    topo = Topology(topology) if topology else route_topology(goal, steps)
    run_id = store.create_swarm_run(goal[:500], topo.value, len(steps))
    specialist_map = specialist_map or {}
    all_results = {}
    max_rounds = getattr(config, "swarm_max_rounds", 10)

    try:
        if topo == Topology.PARALLEL:
            tasks = []
            for i, step in enumerate(steps[:_cap_agents(len(steps))]):
                desc = step.get("description", str(step)) if isinstance(step, dict) else str(step)
                spec = specialist_map.get(i) or step.get("specialist") if isinstance(step, dict) else "researcher"
                tasks.append({"specialist": spec, "task": desc})
            wave_results = await subagent.run_parallel(tasks)
            for i, r in enumerate(wave_results):
                all_results[i] = r

        elif topo in (Topology.SEQUENTIAL, Topology.HIERARCHICAL, Topology.HYBRID):
            waves = topological_waves(steps)
            context_accum = ""
            for wave_idx, wave in enumerate(waves[:max_rounds]):
                if len(wave) == 1:
                    i = wave[0]
                    step = steps[i]
                    desc = step.get("description", str(step)) if isinstance(step, dict) else str(step)
                    if context_accum:
                        desc = f"{desc}\n\nPrior context:\n{context_accum[:2000]}"
                    spec = specialist_map.get(i) or (step.get("specialist") if isinstance(step, dict) else "researcher")
                    r = await subagent.run_subagent(spec, desc)
                    all_results[i] = r
                    context_accum = r.get("result", "")
                else:
                    tasks = []
                    for i in wave[:_cap_agents(len(wave))]:
                        step = steps[i]
                        desc = step.get("description", str(step)) if isinstance(step, dict) else str(step)
                        spec = specialist_map.get(i) or (step.get("specialist") if isinstance(step, dict) else "researcher")
                        tasks.append({"specialist": spec, "task": desc})
                    wave_results = await subagent.run_parallel(tasks)
                    for j, i in enumerate(wave[:len(wave_results)]):
                        all_results[i] = wave_results[j]
                    context_accum = await aggregate_results(goal, wave_results)

        else:
            # Default parallel fan-out for debate/mesh/blackboard (handled by dedicated modules)
            tasks = [{"specialist": "researcher", "task": goal}]
            all_results[0] = await subagent.run_subagent("researcher", goal)

        ordered = [all_results[k] for k in sorted(all_results)]
        synthesis = await aggregate_results(goal, ordered)
        store.finish_swarm_run(run_id, "done", synthesis[:4000])
        return {
            "run_id": run_id,
            "topology": topo.value,
            "results": ordered,
            "synthesis": synthesis,
        }
    except Exception as e:
        logger.error(f"[swarm] run failed: {e}")
        store.finish_swarm_run(run_id, "failed", str(e)[:500])
        return {"run_id": run_id, "error": str(e)}

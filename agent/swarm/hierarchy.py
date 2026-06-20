"""Hierarchical hybrid swarm — nested delegation with depth bounds."""
import logging

from agent import subagent
from agent.swarm.runner import run_swarm, aggregate_results
from agent.swarm.debate import run_debate, run_maker_checker
from agent.swarm.mesh import run_mesh
from config import config

logger = logging.getLogger(__name__)

MAX_DEPTH = 3


async def run_hierarchical(goal: str, layers: list = None, depth: int = 0) -> dict:
    """Compose fan-out, mesh, and debate at hierarchical layers.

    `layers`: [{"mode": "parallel|sequential|debate|mesh", "tasks": [...]}]
    """
    if depth >= MAX_DEPTH:
        return {"error": f"Max hierarchy depth ({MAX_DEPTH}) reached.", "goal": goal}

    if not layers:
        layers = [
            {"mode": "parallel", "tasks": [{"description": f"Research aspect of: {goal}", "specialist": "researcher"}]},
            {"mode": "mesh", "artifact": "", "goal": goal},
            {"mode": "debate", "topic": goal},
        ]

    layer_results = []
    context = ""

    for i, layer in enumerate(layers):
        mode = layer.get("mode", "parallel")
        logger.info(f"[hierarchy] layer {i} mode={mode} depth={depth}")

        if mode == "parallel":
            tasks = layer.get("tasks", [{"description": goal, "specialist": "researcher"}])
            if context:
                for t in tasks:
                    t["description"] = f"{t.get('description', goal)}\n\nPrior:\n{context[:1500]}"
            r = await run_swarm(goal, steps=tasks, topology="parallel")
            layer_results.append(r)
            context = r.get("synthesis", "")

        elif mode == "sequential":
            steps = layer.get("tasks", [{"description": goal, "depends_on": []}])
            r = await run_swarm(goal, steps=steps, topology="sequential")
            layer_results.append(r)
            context = r.get("synthesis", "")

        elif mode == "debate":
            topic = layer.get("topic", goal)
            r = await run_debate(topic)
            layer_results.append(r)
            context = r.get("verdict", "")

        elif mode == "mesh":
            artifact = layer.get("artifact", context or goal)
            mesh_goal = layer.get("goal", goal)
            r = await run_mesh(artifact, mesh_goal, agents=layer.get("agents", 4))
            layer_results.append(r)
            context = r.get("artifact", "")

        elif mode == "nested":
            sub_goal = layer.get("goal", goal)
            sub_layers = layer.get("layers", [])
            r = await run_hierarchical(sub_goal, sub_layers, depth=depth + 1)
            layer_results.append(r)
            context = r.get("synthesis", str(r))

        else:
            r = await subagent.run_subagent("analyst", goal)
            layer_results.append(r)
            context = r.get("result", "")

    synthesis = await aggregate_results(goal, [{"result": context}])
    return {
        "goal": goal,
        "depth": depth,
        "layers_run": len(layer_results),
        "layer_results": layer_results,
        "synthesis": synthesis,
    }

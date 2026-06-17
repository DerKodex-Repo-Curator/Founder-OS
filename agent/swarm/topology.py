"""AdaptOrch-style task-adaptive topology routing.

Maps a task DAG to the optimal orchestration pattern: parallel, sequential,
hierarchical, or hybrid. O(|V|+|E|) analysis of dependency structure.
"""
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Topology(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    HYBRID = "hybrid"
    DEBATE = "debate"
    MESH = "mesh"
    BLACKBOARD = "blackboard"


def _parse_depends(step) -> list:
    if isinstance(step, dict):
        deps = step.get("depends_on") or []
        return [int(d) for d in deps if str(d).isdigit()]
    return []


def _dag_metrics(steps: list) -> dict:
    """Compute width, depth, coupling from a step list with depends_on."""
    n = len(steps)
    if n == 0:
        return {"width": 0, "depth": 0, "coupling": 0, "independent": 0}

    deps = [_parse_depends(s) for s in steps]
    in_degree = [0] * n
    for dlist in deps:
        for d in dlist:
            if 0 <= d < n:
                in_degree[d] += 0  # noqa — track outgoing
    # Build reverse: who depends on whom
    children = [[] for _ in range(n)]
    for i, dlist in enumerate(deps):
        for d in dlist:
            if 0 <= d < n:
                children[d].append(i)

    # Topological levels (wave width)
    level = [0] * n
    for i in range(n):
        for d in deps[i]:
            if 0 <= d < n:
                level[i] = max(level[i], level[d] + 1)
    max_level = max(level) if level else 0
    width = max(sum(1 for l in level if l == lv) for lv in range(max_level + 1))

    independent = sum(1 for d in deps if not d)
    coupling = sum(len(d) for d in deps) / max(n, 1)

    return {
        "width": width,
        "depth": max_level + 1,
        "coupling": coupling,
        "independent": independent,
        "total": n,
    }


def route_topology(goal: str, steps: list = None, hint: str = "") -> Topology:
    """Select orchestration topology from task structure and hints."""
    steps = steps or []
    m = _dag_metrics(steps)
    gl = (goal or "").lower()
    hint_l = (hint or "").lower()

    # Explicit hints override
    if "debate" in hint_l or "argue" in gl or "compare pros and cons" in gl:
        return Topology.DEBATE
    if "mesh" in hint_l or "refine" in gl or "iterate" in gl:
        return Topology.MESH
    if "blackboard" in hint_l or "consensus" in gl:
        return Topology.BLACKBOARD

    if m["total"] == 0:
        if any(w in gl for w in ("research", "compare", "multiple", "parallel")):
            return Topology.PARALLEL
        if any(w in gl for w in ("debate", "decide", "evaluate", "judge")):
            return Topology.DEBATE
        return Topology.SEQUENTIAL

    if m["width"] >= 3 and m["coupling"] < 0.5:
        return Topology.PARALLEL
    if m["depth"] >= 3 and m["width"] >= 2:
        return Topology.HYBRID
    if m["depth"] >= 2:
        return Topology.HIERARCHICAL
    if m["independent"] >= 2:
        return Topology.PARALLEL
    return Topology.SEQUENTIAL


def topological_waves(steps: list) -> list:
    """Return list of waves; each wave is a list of step indices ready to run."""
    n = len(steps)
    if n == 0:
        return []
    deps = [_parse_depends(s) for s in steps]
    done = set()
    waves = []
    while len(done) < n:
        wave = []
        for i in range(n):
            if i in done:
                continue
            if all(d in done for d in deps[i]):
                wave.append(i)
        if not wave:
            # Cycle or bad deps — run remaining sequentially
            wave = [i for i in range(n) if i not in done]
        waves.append(wave)
        done.update(wave)
    return waves

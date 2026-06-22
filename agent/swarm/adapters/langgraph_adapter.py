"""Optional LangGraph adapter — wraps execute_loop nodes behind a feature flag."""
import logging

from config import config

logger = logging.getLogger(__name__)


def langgraph_available() -> bool:
    if not getattr(config, "langgraph_adapter", False):
        return False
    try:
        import langgraph  # noqa: F401
        return True
    except ImportError:
        return False


async def run_langgraph_swarm(goal: str, steps: list = None) -> dict:
    """Run swarm via LangGraph if enabled, else fall back to native runner."""
    if not langgraph_available():
        from agent.swarm.runner import run_swarm
        return await run_swarm(goal, steps=steps)

    try:
        from langgraph.graph import StateGraph, END
        from agent import subagent

        steps = steps or [{"description": goal, "specialist": "researcher"}]
        results = {}

        async def execute_step(state: dict) -> dict:
            idx = state.get("current_step", 0)
            if idx >= len(steps):
                return {**state, "done": True}
            step = steps[idx]
            desc = step.get("description", goal)
            spec = step.get("specialist", "researcher")
            r = await subagent.run_subagent(spec, desc)
            results[idx] = r
            return {**state, "current_step": idx + 1, "results": results}

        graph = StateGraph(dict)
        graph.add_node("execute", execute_step)
        graph.set_entry_point("execute")
        graph.add_conditional_edges("execute", lambda s: "done" if s.get("done") or s.get("current_step", 0) >= len(steps) else "execute", {"execute": "execute", "done": END})
        app = graph.compile()
        final = await app.ainvoke({"goal": goal, "current_step": 0, "results": {}})

        from agent.swarm.runner import aggregate_results
        ordered = [final["results"][k] for k in sorted(final.get("results", {}))]
        synthesis = await aggregate_results(goal, ordered)
        return {"adapter": "langgraph", "results": ordered, "synthesis": synthesis, "state": final}
    except Exception as e:
        logger.warning(f"[langgraph] adapter failed, native fallback: {e}")
        from agent.swarm.runner import run_swarm
        return await run_swarm(goal, steps=steps)

"""LECE tools exposed to the supervisor agent."""
from agent.registry import register


@register(
    name="distill_now",
    description="Run experiential self-distillation: extract principle-level experience "
                "from recent agent traces and update the personalized operating manual.",
    parameters={"type": "object", "properties": {"since_hours": {"type": "integer"}}},
    category="meta",
)
async def tool_distill_now(since_hours: int = 24):
    import time
    from agent.cognition.distill import run_distillation
    since_ts = time.time() - since_hours * 3600 if since_hours else 0
    return await run_distillation(since_ts=since_ts)


@register(
    name="list_principles",
    description="List learned principles from LECE self-distillation with effectiveness scores.",
    parameters={
        "type": "object",
        "properties": {"limit": {"type": "integer"}, "status": {"type": "string"}},
    },
    category="meta",
)
async def tool_list_principles(limit: int = 15, status: str = "active"):
    from agent import store
    rows = store.list_principles(status, limit)
    return {"principles": rows, "count": len(rows)}


@register(
    name="preplay_action",
    description="Simulate a high-stakes action on the business digital twin before executing. "
                "Returns predicted outcomes for candidate variants.",
    parameters={
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "args": {"type": "object"},
            "goal": {"type": "string"},
        },
        "required": ["tool_name"],
    },
    category="meta",
)
async def tool_preplay_action(tool_name: str, args: dict = None, goal: str = ""):
    from agent.cognition.preplay import run_preplay
    return await run_preplay(tool_name, args or {}, goal)


@register(
    name="simulate_strategy",
    description="Run parallel counterfactual strategy rollouts on the digital twin (sandbox).",
    parameters={
        "type": "object",
        "properties": {
            "strategies": {"type": "array", "items": {"type": "string"}},
            "goal": {"type": "string"},
        },
        "required": ["strategies", "goal"],
    },
    category="meta",
)
async def tool_simulate_strategy(strategies: list, goal: str):
    from agent.cognition.preplay import run_preplay
    from agent import subagent
    from agent.cognition import twin, sandbox
    state_text = twin.snapshot_for_preplay()
    tasks = []
    for s in strategies[:5]:
        tasks.append({
            "specialist": "analyst",
            "task": f"SIMULATION. Strategy: {s}\nGoal: {goal}\nTwin:\n{state_text}\n"
                    "Predict outcome. No real actions.",
        })
    with sandbox.SimulationContext():
        results = await subagent.run_parallel(tasks)
    return {"strategies": strategies, "rollouts": results}


@register(
    name="twin_state",
    description="Get the current business digital twin state vector and top procedure transitions.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_twin_state():
    from agent.cognition.twin import twin_summary
    return twin_summary()


@register(
    name="why_did_you",
    description="Explain a recent decision using workspace state, trace, and preplay records.",
    parameters={
        "type": "object",
        "properties": {"trace_id": {"type": "string"}},
    },
    category="meta",
)
async def tool_why_did_you(trace_id: str = ""):
    from agent import trace, store
    from agent.cognition.workspace import render_state
    traces = trace.iter_traces(limit=20)
    match = next((t for t in traces if t.get("id") == trace_id), traces[0] if traces else None)
    preplay = store.list_preplay_runs(5)
    ws = render_state()
    return {
        "trace": match,
        "workspace": ws,
        "recent_preplay": preplay[:3],
    }


@register(
    name="workspace_state",
    description="View the Global Workspace blackboard: active attention items and salience scores.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_workspace_state():
    from agent.cognition.workspace import render_state
    from agent.cognition.processes import run_attention_cycle
    await run_attention_cycle()
    return render_state()


@register(
    name="trust_report",
    description="View learned trust/competence scores per action type for adaptive autonomy.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_trust_report():
    from agent.cognition.trust import trust_report
    return trust_report()


@register(
    name="founder_profile",
    description="View the learned founder theory-of-mind model (preferences, risk, style).",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_founder_profile():
    from agent.cognition.founder_model import get_profile, profile_block
    return {"profile": get_profile(), "block": profile_block()}


@register(
    name="lece_metrics",
    description="Full LECE metrics report: preplay accuracy, principle effectiveness, trust, distillation.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_lece_metrics():
    from agent.cognition.metrics import full_report
    return full_report()

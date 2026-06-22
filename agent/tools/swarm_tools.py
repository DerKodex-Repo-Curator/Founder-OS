"""Swarm orchestration tools — all 12 paths exposed to the supervisor agent."""
from agent.registry import register
from agent import subagent, store
from agent.swarm.runner import run_swarm, aggregate_results
from agent.swarm.topology import route_topology
from agent.swarm.handoff import create_handoff_session, get_handoff_session, run_handoff_chain
from agent.swarm.debate import run_debate, run_maker_checker
from agent.swarm.mesh import run_mesh
from agent.swarm.board import SwarmBoard, run_blackboard_round
from agent.swarm.profiles import assign_agent, run_swarmsys_cycle, list_profiles, reinforce_profile
from agent.swarm.hierarchy import run_hierarchical
from agent.swarm.proactive import run_proactive_swarm
from agent.swarm.evolve import run_evolve_swarm
from agent.swarm.adapters.langgraph_adapter import run_langgraph_swarm, langgraph_available
from agent.swarm.workers.queue import enqueue_job, dequeue_job


_SPECIALISTS = subagent.list_specialists()


@register(
    name="run_swarm",
    description="Execute a multi-agent swarm with adaptive topology (parallel, sequential, "
                "hierarchical, hybrid). Provide a goal and optional steps with depends_on DAG.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "topology": {"type": "string", "enum": ["", "parallel", "sequential", "hierarchical", "hybrid"]},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "depends_on": {"type": "array", "items": {"type": "integer"}},
                        "specialist": {"type": "string"},
                    },
                },
            },
        },
        "required": ["goal"],
    },
    category="orchestration",
)
async def tool_run_swarm(goal: str, topology: str = "", steps: list = None):
    if not steps:
        topo = route_topology(goal)
        return await run_swarm(goal, topology=topo.value)
    return await run_swarm(goal, steps=steps, topology=topology)


@register(
    name="swarm_aggregate",
    description="Synthesize multiple sub-agent results into one coherent answer (fan-in).",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "results": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["goal", "results"],
    },
    category="orchestration",
)
async def tool_swarm_aggregate(goal: str, results: list):
    return {"synthesis": await aggregate_results(goal, results)}


@register(
    name="route_topology",
    description="Analyze a task and recommend the optimal swarm topology (parallel, sequential, "
                "hierarchical, debate, mesh, blackboard).",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["goal"],
    },
    category="orchestration",
)
async def tool_route_topology(goal: str, steps: list = None):
    topo = route_topology(goal, steps or [])
    return {"topology": topo.value, "goal": goal}


@register(
    name="handoff_start",
    description="Start a dynamic peer handoff session (OpenAI Swarm style). Returns session_id.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "start_specialist": {"type": "string", "enum": _SPECIALISTS},
        },
        "required": ["goal"],
    },
    category="orchestration",
)
async def tool_handoff_start(goal: str, start_specialist: str = "researcher"):
    return await run_handoff_chain(goal, start_specialist)


@register(
    name="handoff_to",
    description="Transfer control to another specialist within an active handoff session.",
    parameters={
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "to_specialist": {"type": "string", "enum": _SPECIALISTS},
            "reason": {"type": "string"},
            "task": {"type": "string"},
        },
        "required": ["session_id", "to_specialist"],
    },
    category="orchestration",
)
async def tool_handoff_to(session_id: str, to_specialist: str, reason: str = "", task: str = ""):
    session = get_handoff_session(session_id)
    if not session:
        return {"error": f"Unknown session '{session_id}'."}
    return await session.handoff(to_specialist, reason, task)


@register(
    name="run_debate",
    description="Multi-agent debate with advocate/skeptic roles and judge synthesis. "
                "Best for strategic decisions and evaluations.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "rounds": {"type": "integer"},
        },
        "required": ["topic"],
    },
    category="orchestration",
)
async def tool_run_debate(topic: str, rounds: int = 2):
    return await run_debate(topic, rounds=rounds)


@register(
    name="run_maker_checker",
    description="Maker-checker loop: one agent drafts, another validates, until approved.",
    parameters={
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "max_iterations": {"type": "integer"},
        },
        "required": ["task"],
    },
    category="orchestration",
)
async def tool_run_maker_checker(task: str, max_iterations: int = 3):
    return await run_maker_checker(task, max_iterations)


@register(
    name="run_mesh",
    description="Mesh coordination: 3-8 agents iterate on a shared artifact until quality converges.",
    parameters={
        "type": "object",
        "properties": {
            "artifact": {"type": "string"},
            "goal": {"type": "string"},
            "agents": {"type": "integer"},
            "max_rounds": {"type": "integer"},
        },
        "required": ["artifact", "goal"],
    },
    category="orchestration",
)
async def tool_run_mesh(artifact: str, goal: str, agents: int = 4, max_rounds: int = 5):
    return await run_mesh(artifact, goal, agents=agents, max_rounds=max_rounds)


@register(
    name="run_blackboard",
    description="Blackboard/stigmergic swarm: agents post findings to a shared board until consensus.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "max_rounds": {"type": "integer"},
        },
        "required": ["topic"],
    },
    category="orchestration",
)
async def tool_run_blackboard(topic: str, max_rounds: int = 5):
    return await run_blackboard_round(topic, max_rounds)


@register(
    name="board_post",
    description="Post a finding to an active swarm blackboard (stigmergic trace).",
    parameters={
        "type": "object",
        "properties": {
            "run_id": {"type": "integer"},
            "agent": {"type": "string"},
            "entry_type": {"type": "string"},
            "content": {"type": "string"},
            "salience": {"type": "number"},
        },
        "required": ["run_id", "agent", "content"],
    },
    category="orchestration",
)
async def tool_board_post(run_id: int, agent: str, content: str, entry_type: str = "finding", salience: float = 1.0):
    board = SwarmBoard(run_id, "")
    eid = board.post(agent, entry_type, content, salience)
    return {"entry_id": eid}


@register(
    name="board_read",
    description="Read entries from a swarm blackboard, ordered by salience.",
    parameters={
        "type": "object",
        "properties": {
            "run_id": {"type": "integer"},
            "limit": {"type": "integer"},
        },
        "required": ["run_id"],
    },
    category="orchestration",
)
async def tool_board_read(run_id: int, limit: int = 20):
    board = SwarmBoard(run_id, "")
    return {"entries": board.read(limit)}


@register(
    name="assign_swarm_agent",
    description="Bio-inspired agent assignment: match task to best agent profile by embedding + pheromone.",
    parameters={
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "role": {"type": "string", "enum": ["explorer", "worker", "validator"]},
        },
        "required": ["task"],
    },
    category="orchestration",
)
async def tool_assign_swarm_agent(task: str, role: str = "worker"):
    return await assign_agent(task, role)


@register(
    name="run_swarmsys",
    description="Full SwarmSys cycle: explorer + worker + validator with pheromone reinforcement.",
    parameters={
        "type": "object",
        "properties": {"task": {"type": "string"}},
        "required": ["task"],
    },
    category="orchestration",
)
async def tool_run_swarmsys(task: str):
    return await run_swarmsys_cycle(task)


@register(
    name="run_hierarchical_swarm",
    description="Hierarchical hybrid swarm composing parallel, mesh, and debate layers.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "layers": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["goal"],
    },
    category="orchestration",
)
async def tool_run_hierarchical(goal: str, layers: list = None):
    return await run_hierarchical(goal, layers)


@register(
    name="run_proactive_swarm",
    description="Run budget-aware swarm over active goals (for heartbeat/proactive use).",
    parameters={"type": "object", "properties": {"context": {"type": "string"}}},
    category="orchestration",
)
async def tool_run_proactive_swarm(context: str = ""):
    return await run_proactive_swarm(context)


@register(
    name="run_evolve_swarm",
    description="Self-evolving swarm that executes work and may propose new reusable skills.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "propose_skill": {"type": "boolean"},
        },
        "required": ["goal"],
    },
    category="orchestration",
)
async def tool_run_evolve_swarm(goal: str, propose_skill: bool = True):
    return await run_evolve_swarm(goal, propose_skill)


@register(
    name="enqueue_swarm_job",
    description="Enqueue a swarm job for async/distributed execution (SQLite or Redis queue).",
    parameters={
        "type": "object",
        "properties": {
            "job_type": {"type": "string", "enum": ["swarm", "debate", "mesh", "blackboard"]},
            "goal": {"type": "string"},
            "payload": {"type": "object"},
            "priority": {"type": "integer"},
        },
        "required": ["job_type", "goal"],
    },
    category="orchestration",
)
async def tool_enqueue_swarm_job(job_type: str, goal: str, payload: dict = None, priority: int = 5):
    payload = payload or {}
    payload["goal"] = goal
    job_id = enqueue_job(job_type, payload, priority)
    return {"job_id": job_id, "status": "queued"}


@register(
    name="list_swarm_runs",
    description="List recent swarm execution runs with topology and status.",
    parameters={
        "type": "object",
        "properties": {"limit": {"type": "integer"}},
    },
    category="orchestration",
)
async def tool_list_swarm_runs(limit: int = 10):
    return {"runs": store.list_swarm_runs(limit)}


@register(
    name="list_swarm_profiles",
    description="List bio-inspired swarm agent profiles with pheromone scores.",
    parameters={
        "type": "object",
        "properties": {"role": {"type": "string"}},
    },
    category="orchestration",
)
async def tool_list_swarm_profiles(role: str = None):
    return {"profiles": list_profiles(role)}


@register(
    name="run_langgraph_swarm",
    description="Run swarm via optional LangGraph adapter (falls back to native if unavailable).",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["goal"],
    },
    category="orchestration",
)
async def tool_run_langgraph_swarm(goal: str, steps: list = None):
    return await run_langgraph_swarm(goal, steps)


@register(
    name="swarm_status",
    description="Get swarm system status: config, recent runs, profiles, LangGraph availability.",
    parameters={"type": "object", "properties": {}},
    category="orchestration",
)
async def tool_swarm_status():
    from config import config
    return {
        "enabled": config.swarm_enabled,
        "max_agents": config.swarm_max_agents,
        "worker_mode": config.swarm_worker_mode,
        "langgraph_available": langgraph_available(),
        "specialists": _SPECIALISTS,
        "recent_runs": store.list_swarm_runs(5),
        "profiles": list_profiles()[:10],
    }

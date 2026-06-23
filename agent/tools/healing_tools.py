"""Self-healing diagnostic and control tools."""
from agent.registry import register
from agent.healing.watchdog import run_self_test, auto_remediate, watchdog_tick
from agent.healing.ledger import recent_failures, failure_stats, recall_similar
from agent.healing.circuit import all_circuits, record_success
from agent.healing.router import clear_blocks
from agent.healing.storage import full_storage_health
from agent import store


@register(
    name="run_self_test",
    description="Run a comprehensive self-test of all critical subsystems: SQLite, vector store, "
                "tools, generated tools, budget, circuit breakers, and healing status.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_run_self_test():
    return await run_self_test()


@register(
    name="health_report",
    description="Get a full health report: self-test results, failure stats, circuit breaker "
                "states, storage health, and recent healing events.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_health_report():
    test = await run_self_test()
    return {
        "self_test": test,
        "failure_stats": failure_stats(),
        "circuits": all_circuits(),
        "storage": full_storage_health(),
        "recent_healing_events": store.list_healing_events(10),
    }


@register(
    name="heal_now",
    description="Trigger immediate self-healing: run self-test and auto-remediate any detected "
                "issues (DB reconnect, vector store repair, reset stale circuit breakers).",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_heal_now():
    result = await watchdog_tick()
    clear_blocks()
    return result


@register(
    name="failure_log",
    description="List recent failures recorded by the self-healing system, with diagnosis "
                "and recovery actions taken.",
    parameters={
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "limit": {"type": "integer"},
        },
    },
    category="meta",
)
async def tool_failure_log(tool_name: str = "", limit: int = 20):
    if tool_name:
        return {"failures": recall_similar(tool_name=tool_name, limit=limit)}
    return {"failures": recent_failures(limit)}


@register(
    name="circuit_status",
    description="Show circuit breaker states for all monitored providers and tools.",
    parameters={"type": "object", "properties": {}},
    category="meta",
)
async def tool_circuit_status():
    circuits = all_circuits()
    open_circuits = [c for c in circuits if c.get("state") == "open"]
    return {
        "total": len(circuits),
        "open": len(open_circuits),
        "circuits": circuits,
    }


@register(
    name="reset_circuit",
    description="Manually reset a circuit breaker to CLOSED state (e.g. after fixing an external service).",
    parameters={
        "type": "object",
        "properties": {"key": {"type": "string", "description": "Circuit key, e.g. tool:web_search or llm:groq"}},
        "required": ["key"],
    },
    category="meta",
)
async def tool_reset_circuit(key: str):
    record_success(key)
    return {"reset": True, "key": key, "state": "closed"}

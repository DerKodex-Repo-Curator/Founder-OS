"""Watchdog — periodic self-test and auto-remediation."""
import logging

from agent import registry
from agent.healing import circuit, storage
from config import config

logger = logging.getLogger(__name__)


async def run_self_test() -> dict:
    """Comprehensive health check of all critical subsystems."""
    results = {}

    # SQLite
    results["sqlite"] = storage.check_sqlite()

    # Vector store
    results["vector"] = storage.check_vector_store()

    # Tools registered
    tools = registry.all_tools()
    results["tools"] = {"ok": len(tools) > 0, "count": len(tools)}

    # Generated tools load
    try:
        from agent import skills_factory
        gen_count = skills_factory.load_generated()
        results["generated_tools"] = {"ok": True, "count": gen_count}
    except Exception as e:
        results["generated_tools"] = {"ok": False, "error": str(e)[:100]}

    # LLM reachability (lightweight — budget check only)
    try:
        from agent import budget
        budget.check_before_call()
        results["budget"] = {"ok": True, "paused": config.agent_paused}
    except Exception as e:
        results["budget"] = {"ok": False, "error": str(e)[:100]}

    # Circuit breakers
    circuits = circuit.all_circuits()
    open_count = sum(1 for c in circuits if c.get("state") == "open")
    results["circuits"] = {"ok": open_count == 0, "open": open_count, "total": len(circuits)}

    # Healing enabled
    results["healing"] = {"ok": True, "enabled": getattr(config, "healing_enabled", True)}

    all_ok = all(
        r.get("ok", False) for r in results.values() if isinstance(r, dict)
    )
    return {"healthy": all_ok, "components": results}


async def auto_remediate() -> dict:
    """Attempt to fix detected issues."""
    fixes = []

    if not storage.check_sqlite()["ok"]:
        r = storage.repair_sqlite()
        fixes.append({"component": "sqlite", **r})

    if not storage.check_vector_store()["ok"]:
        r = storage.repair_vector_store()
        fixes.append({"component": "vector", **r})

    # Reset stale open circuits older than 2x cooldown
    from agent.healing.circuit import _cooldown_s
    import time
    for c in circuit.all_circuits():
        if c.get("state") == "open":
            opened = c.get("opened_at") or 0
            if time.time() - float(opened or 0) > _cooldown_s() * 2:
                circuit.record_success(c["key"])
                fixes.append({"component": f"circuit:{c['key']}", "reset": True})

    return {"remediated": len(fixes) > 0, "fixes": fixes}


async def watchdog_tick():
    """Single watchdog cycle: test + remediate."""
    if not getattr(config, "watchdog_enabled", True):
        return {"skipped": True}
    test = await run_self_test()
    if not test.get("healthy"):
        remed = await auto_remediate()
        return {"test": test, "remediation": remed}
    return {"test": test, "remediation": None}

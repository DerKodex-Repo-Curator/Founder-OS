"""Shared dashboard state collection."""
import logging

logger = logging.getLogger(__name__)


def _safe(fn, default):
    try:
        return fn()
    except Exception as e:
        logger.debug(f"[state] {getattr(fn, '__name__', fn)} failed: {e}")
        return default


def collect_state() -> dict:
    from agent import about, budget, finance, store
    from memory import world_model
    import agent.trace as trace
    return {
        "about": _safe(about.describe, {}),
        "snapshot": _safe(world_model.build_snapshot, {}),
        "usage": _safe(budget.status, {}),
        "finance": _safe(finance.summary, {}),
        "approvals": _safe(store.list_pending_approvals, []),
        "goals": _safe(lambda: store.list_goals("active"), []),
        "traces": _safe(lambda: trace.recent(10), []),
        "actions": _safe(lambda: store.recent_actions(15), []),
        "usage_history": _safe(lambda: store.usage_history(7), []),
    }

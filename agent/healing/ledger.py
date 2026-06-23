"""Failure ledger — persist and recall failure->diagnosis->fix patterns."""
import logging

from agent import store

logger = logging.getLogger(__name__)


def record_failure(actor: str, kind: str, failure_class: str, signal: str,
                     tool_name: str = "", diagnosis: str = "", recovery_action: str = "",
                     recovered: bool = False, trace_id: str = ""):
    try:
        store.log_failure(
            actor, kind, failure_class, signal[:500], tool_name,
            diagnosis[:500], recovery_action, recovered, trace_id,
        )
    except Exception as e:
        logger.debug(f"[healing/ledger] record failed: {e}")


def recall_similar(tool_name: str = "", failure_class: str = "", limit: int = 5) -> list:
    """Recall past failures for the same tool/class to inform recovery."""
    return store.recall_failures(tool_name, failure_class, limit)


def recent_failures(limit: int = 20) -> list:
    return store.list_failures(limit)


def failure_stats() -> dict:
    rows = store.list_failures(100)
    total = len(rows)
    recovered = sum(1 for r in rows if r.get("recovered"))
    by_class = {}
    for r in rows:
        fc = r.get("failure_class", "unknown")
        by_class[fc] = by_class.get(fc, 0) + 1
    return {
        "total": total,
        "recovered": recovered,
        "recovery_rate": round(recovered / max(total, 1), 2),
        "by_class": by_class,
    }

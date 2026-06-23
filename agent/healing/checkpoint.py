"""Checkpoint + rollback and compensating transactions."""
import json
import logging
import uuid

from agent import store

logger = logging.getLogger(__name__)

# Undo handlers for write tools (best-effort compensating actions)
_COMPENSATIONS = {
    "set_reminder": lambda args: {"action": "cancel_reminder", "id": args.get("reminder_id")},
    "add_task": lambda args: {"action": "complete_task", "id": args.get("task_id")},
    "add_goal": lambda args: {"action": "update_goal", "id": args.get("goal_id"), "status": "dropped"},
}


def start_turn(turn_id: str = None) -> str:
    tid = turn_id or uuid.uuid4().hex[:12]
    return tid


def checkpoint(turn_id: str, step: int, snapshot: dict) -> int:
    return store.save_checkpoint(turn_id, step, json.dumps(snapshot, default=str)[:8000])


def latest_checkpoint(turn_id: str) -> dict:
    row = store.get_latest_checkpoint(turn_id)
    if not row:
        return {}
    try:
        return {"step": row["step"], "snapshot": json.loads(row["snapshot_json"] or "{}")}
    except Exception:
        return {}


def rollback(turn_id: str) -> dict:
    """Restore to latest checkpoint snapshot."""
    cp = latest_checkpoint(turn_id)
    if not cp:
        return {"rolled_back": False, "reason": "no_checkpoint"}
    logger.info(f"[healing/checkpoint] rollback turn={turn_id} step={cp.get('step')}")
    return {"rolled_back": True, "step": cp.get("step"), "snapshot": cp.get("snapshot")}


def record_compensation(tool_name: str, args: dict, result: dict, turn_id: str):
    """Record a compensating action for a write tool."""
    if tool_name not in _COMPENSATIONS:
        return
    undo = _COMPENSATIONS[tool_name](args)
    store.save_checkpoint(turn_id, -1, json.dumps({
        "compensation": undo, "tool": tool_name, "args": args, "result_preview": str(result)[:200],
    }, default=str))


async def execute_compensations(turn_id: str) -> list:
    """Run recorded compensations for a turn (best-effort)."""
    rows = store.list_checkpoints(turn_id, compensation_only=True)
    results = []
    for row in rows:
        try:
            data = json.loads(row.get("snapshot_json") or "{}")
            comp = data.get("compensation")
            if comp:
                results.append({"compensation": comp, "status": "recorded"})
        except Exception:
            pass
    return results

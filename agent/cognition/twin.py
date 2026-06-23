"""Business digital twin: state vector + procedure graph."""
import hashlib
import json

from agent import store
from memory import world_model

from config import config


def build_state_vector() -> dict:
    """Structured business state extending world_model snapshot."""
    snap = world_model.build_snapshot()
    return {
        "ts": snap.get("ts"),
        "crm": snap.get("crm", {}),
        "tasks_open": snap.get("tasks_open", 0),
        "goals": snap.get("goals_active", []),
        "approvals_pending": snap.get("approvals_pending", 0),
        "finance": snap.get("finance", {}),
        "strategies": snap.get("top_strategies", []),
    }


def state_key(state: dict = None) -> str:
    """Compact hash key for transition lookup."""
    s = state or build_state_vector()
    blob = json.dumps({
        "crm": s.get("crm", {}).get("by_status", {}),
        "tasks": s.get("tasks_open", 0),
        "approvals": s.get("approvals_pending", 0),
        "goals_n": len(s.get("goals", [])),
    }, sort_keys=True, default=str)
    return hashlib.md5(blob.encode()).hexdigest()[:16]


def action_key(tool_name: str, args: dict = None) -> str:
    args = args or {}
    sig = json.dumps({k: str(v)[:80] for k, v in sorted(args.items())}, sort_keys=True)
    return f"{tool_name}:{hashlib.md5(sig.encode()).hexdigest()[:12]}"


def predict_outcome(state: dict, tool_name: str, args: dict = None) -> dict:
    """Estimate outcome from procedure graph transitions."""
    sk = state_key(state)
    ak = action_key(tool_name, args)
    rows = store.list_twin_transitions(sk, limit=20)
    matching = [r for r in rows if r["action_key"].startswith(tool_name)]
    if not matching:
        return {"predicted": "unknown", "confidence": 0.3, "reliability": 0.3}
    best = max(matching, key=lambda r: r.get("reliability", 0))
    return {
        "predicted": best.get("outcome_key", "success"),
        "confidence": best.get("reliability", 0.5),
        "reliability": best.get("reliability", 0.5),
        "effect": best.get("effect_estimate", 0.0),
    }


def record_transition(tool_name: str, args: dict, outcome: str, success: bool,
                      effect: float = 0.0, state: dict = None):
    sk = state_key(state)
    ak = action_key(tool_name, args)
    store.upsert_twin_transition(sk, ak, outcome[:200], success, effect)


def bootstrap_from_logs(limit: int = 100):
    """Seed procedure graph from action_log + strategies."""
    for row in store.recent_actions(limit):
        tool = row.get("tool_name", "")
        result = (row.get("result") or "")[:200]
        success = "error" not in result.lower() and "fail" not in result.lower()
        try:
            args = json.loads(row.get("args_json") or "{}")
        except Exception:
            args = {}
        record_transition(tool, args, result, success, 1.0 if success else -0.5)
    for s in store.all_strategies(30):
        rate = s.get("successes", 0) / max(s.get("trials", 1), 1)
        store.upsert_twin_transition(
            "strategy", s["grp"], s["variant"], rate >= 0.5, rate,
        )


def snapshot_for_preplay() -> str:
    """Text snapshot injected into simulation rollouts."""
    s = build_state_vector()
    lines = [
        f"Twin snapshot @ {s.get('ts')}",
        f"CRM: {s.get('crm', {})}",
        f"Open tasks: {s.get('tasks_open')} | Pending approvals: {s.get('approvals_pending')}",
    ]
    if s.get("goals"):
        lines.append("Goals: " + "; ".join(s["goals"][:5]))
    fin = s.get("finance") or {}
    if fin.get("set"):
        lines.append(f"Finance: cash=${fin.get('cash',0):,.0f}, runway={fin.get('runway_months','?')}mo")
    return "\n".join(lines)[:1500]


def twin_summary() -> dict:
    if not getattr(config, "lece_enabled", True):
        return {"enabled": False}
    bootstrap_from_logs(50)
    state = build_state_vector()
    transitions = store.list_twin_transitions(limit=10)
    return {
        "enabled": True,
        "state_key": state_key(state),
        "state": state,
        "top_transitions": transitions[:5],
    }

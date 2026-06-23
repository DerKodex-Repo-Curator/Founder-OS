"""Attention coalitions that bid for Global Workspace access."""
import logging

from agent import store
from agent.cognition import workspace
from config import config

logger = logging.getLogger(__name__)


async def coalition_perception() -> dict:
    """Inbox/monitors — surface pending external signals."""
    salience = 0.5
    content_parts = []
    try:
        approvals = store.list_pending_approvals()
        if approvals:
            salience = 1.5
            content_parts.append(f"{len(approvals)} approval(s) pending")
    except Exception:
        pass
    try:
        reminders = store.get_pending_reminders()
        if reminders:
            salience = max(salience, 1.2)
            content_parts.append(f"{len(reminders)} reminder(s) due")
    except Exception:
        pass
    if not content_parts:
        return {"salience": 0.0, "content": ""}
    return {"salience": salience, "content": "; ".join(content_parts), "coalition": "perception"}


async def coalition_goals() -> dict:
    goals = store.list_goals("active")[:5]
    if not goals:
        return {"salience": 0.0, "content": ""}
    titles = [g["title"] for g in goals]
    return {
        "salience": 1.0 + 0.1 * len(goals),
        "content": "Active goals: " + "; ".join(titles),
        "coalition": "goals",
    }


async def coalition_healing() -> dict:
    failures = store.list_failures(5)
    recent_unrecovered = [f for f in failures if not f.get("recovered")]
    if not recent_unrecovered:
        return {"salience": 0.0, "content": ""}
    return {
        "salience": 1.3,
        "content": f"{len(recent_unrecovered)} recent unrecovered failure(s)",
        "coalition": "healing",
    }


async def coalition_twin_risk() -> dict:
    try:
        from agent.cognition.twin import build_state_vector
        s = build_state_vector()
        risk = 0.5
        if s.get("approvals_pending", 0) > 2:
            risk += 0.3
        fin = s.get("finance") or {}
        if fin.get("status") in ("critical", "warning"):
            risk += 0.4
        if risk < 0.7:
            return {"salience": 0.0, "content": ""}
        return {
            "salience": risk,
            "content": f"Twin risk elevated: approvals={s.get('approvals_pending')}, "
                       f"finance={fin.get('status', 'ok')}",
            "coalition": "twin_risk",
        }
    except Exception:
        return {"salience": 0.0, "content": ""}


COALITIONS = [
    coalition_perception,
    coalition_goals,
    coalition_healing,
    coalition_twin_risk,
]


async def run_attention_cycle() -> dict:
    """One attention economy tick: coalitions bid, winners post to workspace."""
    if not getattr(config, "lece_enabled", True):
        return {"skipped": True}
    winners = []
    for fn in COALITIONS:
        try:
            bid = await fn()
            if bid.get("salience", 0) >= 0.5 and bid.get("content"):
                workspace.post_item(
                    bid.get("coalition", "unknown"),
                    bid["content"],
                    salience=bid["salience"],
                    coalition=bid.get("coalition", ""),
                )
                winners.append(bid)
        except Exception as e:
            logger.debug(f"[processes] coalition error: {e}")
    workspace.tick_decay()
    return {"winners": len(winners), "coalitions": [w.get("coalition") for w in winners]}

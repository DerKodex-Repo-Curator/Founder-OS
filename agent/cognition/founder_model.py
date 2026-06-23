"""Founder theory-of-mind model for LECE."""
import json
import logging

from agent import store

logger = logging.getLogger(__name__)

DEFAULT_TRAITS = {
    "risk_tolerance": "balanced",
    "communication_style": "direct",
    "decision_speed": "moderate",
}


def get_profile() -> dict:
    traits = store.get_founder_traits()
    out = dict(DEFAULT_TRAITS)
    for k, v in traits.items():
        out[k] = v["value"]
    return out


def learn_from_interaction(message: str, reply: str, tools_used: list = None):
    """Heuristic trait updates from interaction patterns."""
    msg_l = (message or "").lower()
    if any(w in msg_l for w in ("careful", "slow", "review", "approve")):
        store.set_founder_trait("risk_tolerance", "cautious", 0.6)
    if any(w in msg_l for w in ("fast", "just do", "go ahead", "ship")):
        store.set_founder_trait("risk_tolerance", "aggressive", 0.6)
        store.set_founder_trait("decision_speed", "fast", 0.55)
    if len(message or "") < 30:
        store.set_founder_trait("communication_style", "brief", 0.5)


def profile_block() -> str:
    p = get_profile()
    traits = store.get_founder_traits()
    lines = ["── FOUNDER MODEL (theory of mind) ──"]
    for k, v in p.items():
        conf = traits.get(k, {}).get("confidence", 0.5)
        lines.append(f"- {k}: {v} (conf={conf:.0%})")
    return "\n".join(lines)


def risk_multiplier() -> float:
    """Scale factor for autonomy decisions."""
    p = get_profile()
    rt = p.get("risk_tolerance", "balanced")
    if rt == "cautious":
        return 0.7
    if rt == "aggressive":
        return 1.2
    return 1.0

"""Trust-calibrated adaptive autonomy."""
import logging

from agent import policy
from agent import store
from agent.healing import ledger
from config import config

logger = logging.getLogger(__name__)


def _base_decide(tool, args: dict) -> str:
    return policy.decide(tool, args)


def adaptive_decide(tool, args: dict) -> str:
    """Extend static policy with learned competence + twin risk."""
    base = _base_decide(tool, args)
    if not getattr(config, "lece_enabled", True):
        return base
    if not getattr(config, "lece_adaptive_autonomy", True):
        return base
    if tool is None:
        return base

    # Never weaken static floor: if base says approve, keep approve
    if base == "approve":
        return "approve"

    action_type = tool.name
    trust = store.get_trust_score(action_type)
    min_trials = getattr(config, "lece_trust_min_trials", 5)

    if trust.get("trials", 0) < min_trials:
        return base

    competence = trust.get("competence", 0.5)

    # Recall failure ledger for this tool
    past_failures = ledger.recall_similar(tool_name=action_type, limit=3)
    if past_failures and not all(f.get("recovered") for f in past_failures):
        if base == "allow" and getattr(tool, "requires_approval", False) is False:
            if action_type in policy._WRITE_TOOLS:
                return "approve"

    try:
        from agent.cognition.founder_model import risk_multiplier
        competence *= risk_multiplier()
    except Exception:
        pass

    # High competence on non-approval tools can stay allow; low competence escalates
    if base == "allow" and competence < 0.35:
        if action_type in policy._WRITE_TOOLS:
            return "approve"

    if base == "allow" and competence >= 0.85 and min_trials <= trust.get("trials", 0):
        if getattr(tool, "requires_approval", False) and config.autonomy_level != "cautious":
            if not config.auto_approve and config.autonomy_level == "autonomous":
                return "allow"

    return base


def record_outcome(tool_name: str, success: bool):
    store.record_trust_outcome(tool_name, success)


def trust_report() -> dict:
    scores = store.list_trust_scores(30)
    return {
        "adaptive_enabled": getattr(config, "lece_adaptive_autonomy", True),
        "min_trials": getattr(config, "lece_trust_min_trials", 5),
        "scores": scores,
    }

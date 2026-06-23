"""Graceful degradation and human escalation."""
import logging

from config import config

logger = logging.getLogger(__name__)


def degrade(partial_result: str = "", reason: str = "", cached: str = "") -> str:
    """Return a degraded but useful response instead of total failure."""
    if cached:
        return f"(Using cached/prior data) {cached[:1500]}"
    if partial_result:
        return (
            f"I hit a snag ({reason[:100]}), but here's what I have so far:\n\n"
            f"{partial_result[:1500]}\n\n"
            f"Ask me to continue or retry if you need more."
        )
    return (
        f"I wasn't able to complete this fully ({reason[:100]}). "
        f"Try rephrasing or ask me to retry with `heal_now`."
    )


async def escalate_to_founder(summary: str, diagnosis: str = "") -> dict:
    """Surface unrecoverable failure to founder via Telegram (non-blocking)."""
    if not getattr(config, "healing_escalate", True):
        return {"escalated": False, "reason": "escalation_disabled"}

    text = f"*Self-healing escalation*\n\n{summary[:800]}"
    if diagnosis:
        text += f"\n\nDiagnosis: {diagnosis[:400]}"

    try:
        from scheduler.jobs import send_to_user
        await send_to_user(text)
        return {"escalated": True, "channel": "telegram"}
    except Exception as e:
        logger.debug(f"[healing/escalate] telegram failed: {e}")
        return {"escalated": False, "error": str(e)[:200], "summary": summary[:500]}

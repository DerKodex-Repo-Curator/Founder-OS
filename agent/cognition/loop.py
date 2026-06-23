"""Continuous Global Workspace cognitive loop."""
import asyncio
import logging
import math
import random

from config import config

logger = logging.getLogger(__name__)

_task = None
_running = False


def _entropy(items: list) -> float:
    """Semantic diversity proxy for intrinsic drive (GWA-style)."""
    if not items:
        return 0.0
    sources = [i.get("coalition") or i.get("source", "") for i in items]
    counts = {}
    for s in sources:
        counts[s] = counts.get(s, 0) + 1
    n = len(sources)
    ent = 0.0
    for c in counts.values():
        p = c / n
        ent -= p * math.log(p + 1e-9)
    return ent


async def _tick(send_notify=None):
    from agent.cognition import processes, workspace
    from agent import budget

    if config.agent_paused:
        return
    try:
        budget.check_before_call()
    except Exception:
        return

    att = await processes.run_attention_cycle()
    block = workspace.broadcast_block()
    items = workspace.render_state().get("items", [])
    ent = _entropy(items)

    # Intrinsic drive: if entropy low (stagnation), inject exploration nudge
    if ent < 0.3 and random.random() < 0.2:
        workspace.post_item(
            "intrinsic_drive",
            "Cognitive stagnation detected — consider proactive goal review or outreach.",
            salience=1.1,
            coalition="drive",
        )

    # Only act if high-salience winner exists
    winners = att.get("winners", 0)
    if winners >= 1 and send_notify:
        top = workspace.render_state().get("items", [])
        if top and top[0].get("salience", 0) >= 1.2:
            msg = top[0].get("content", "")[:300]
            if msg:
                try:
                    await send_notify(f"🧠 *Workspace*\n\n{msg}")
                except Exception:
                    pass

    # Optional deliberation via core.run for high-salience items
    if winners >= 2:
        try:
            from agent import core
            prompt = (
                "[WORKSPACE TICK] Autonomous cognitive cycle. Workspace state:\n"
                f"{block[:800]}\n\nIf something genuinely useful, act briefly. "
                "Otherwise reply NOTHING."
            )
            reply = await core.run(prompt, actor="workspace")
            if reply and reply.strip().upper() != "NOTHING" and send_notify:
                await send_notify(f"🧠 *Cognitive update*\n\n{reply[:500]}")
        except Exception as e:
            logger.debug(f"[cognition/loop] deliberation skipped: {e}")


async def _loop(send_notify=None):
    global _running
    _running = True
    tick_s = max(30, getattr(config, "lece_workspace_tick_s", 120))
    logger.info(f"[LECE] Continuous workspace loop started (tick={tick_s}s)")
    while _running:
        try:
            await _tick(send_notify)
        except Exception as e:
            logger.debug(f"[LECE] tick error: {e}")
        await asyncio.sleep(tick_s)
    logger.info("[LECE] Continuous workspace loop stopped")


def start_cognitive_loop(app=None):
    """Launch background cognitive loop via post_init hook."""
    global _task, _running
    if not getattr(config, "lece_enabled", True):
        return
    if not getattr(config, "lece_workspace_continuous", False):
        return
    if _task and not _task.done():
        return

    async def _send(text):
        from scheduler.jobs import send_to_user
        await send_to_user(text)

    async def _runner():
        await _loop(_send)

    _task = asyncio.create_task(_runner())


def stop_cognitive_loop():
    global _running, _task
    _running = False
    if _task and not _task.done():
        _task.cancel()
    _task = None

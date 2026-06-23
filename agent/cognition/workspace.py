"""Global Workspace blackboard with salience and broadcast."""
import logging

from agent import store
from config import config

logger = logging.getLogger(__name__)


def post_item(source: str, content: str, salience: float = 1.0, coalition: str = ""):
    if not getattr(config, "lece_enabled", True):
        return None
    return store.workspace_post(source, content, salience, coalition=coalition)


def tick_decay(factor: float = 0.95):
    store.workspace_decay_all(factor)


def broadcast_block(limit: int = 8) -> str:
    """Highest-salience items for prompt injection."""
    if not getattr(config, "lece_enabled", True):
        return ""
    items = store.workspace_read(limit)
    if not items:
        return ""
    lines = ["── GLOBAL WORKSPACE (attention broadcast) ──"]
    for it in items:
        lines.append(f"[{it['source']}|s={it['salience']:.1f}] {it['content'][:200]}")
    return "\n".join(lines)


def render_state() -> dict:
    items = store.workspace_read(20)
    return {
        "active_items": len(items),
        "items": [
            {"source": i["source"], "content": i["content"][:150],
             "salience": i["salience"], "coalition": i.get("coalition", "")}
            for i in items
        ],
    }

"""Personalized Operating Manual — Tier A internalization without weight updates."""
import os

from agent import store

MANUAL_PATH = "./data/agent_state/lece_manual.md"


def rebuild_manual(max_principles: int = 12):
    """Rebuild compact manual from top principles."""
    principles = store.list_principles("active", max_principles)
    if not principles:
        return ""
    os.makedirs(os.path.dirname(MANUAL_PATH), exist_ok=True)
    lines = [
        "# LECE Personalized Operating Manual",
        "",
        "Distilled from this founder's lived agent experience (principle-level, off-policy).",
        "",
    ]
    for p in principles:
        eff = p.get("effectiveness", 0)
        lines.append(f"- ({eff:.0%} effective) {p['principle']}")
    text = "\n".join(lines) + "\n"
    try:
        with open(MANUAL_PATH, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass
    return text


def build_manual_prefix(max_chars: int = 1500) -> str:
    """Return manual block for system prompt injection."""
    if os.path.exists(MANUAL_PATH):
        try:
            with open(MANUAL_PATH, "r", encoding="utf-8") as f:
                return f.read()[:max_chars]
        except Exception:
            pass
    rebuild_manual()
    if os.path.exists(MANUAL_PATH):
        try:
            with open(MANUAL_PATH, "r", encoding="utf-8") as f:
                return f.read()[:max_chars]
        except Exception:
            pass
    return ""

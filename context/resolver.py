"""Resolve which Context Space applies to a user message."""
import logging
import re
from typing import Optional

from memory import context_store, vector_store

logger = logging.getLogger(__name__)

HIGH_CONFIDENCE_MARGIN = 0.15
MIN_SEMANTIC_SCORE = 0.35


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _explicit_matches(message: str) -> dict:
    """Return {space_id: score} for explicit name/alias mentions."""
    msg = _normalize(message)
    scores: dict = {}
    for item in context_store.all_trigger_phrases():
        phrase = _normalize(item["phrase"])
        if len(phrase) < 2:
            continue
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, msg):
            sid = item["space_id"]
            # Longer phrase = stronger signal
            scores[sid] = max(scores.get(sid, 0), 1.0 + len(phrase) / 100)
    return scores


def _semantic_matches(message: str, n_results: int = 8) -> dict:
    """Return {space_id: score} from vector search over documents with space_id."""
    scores: dict = {}
    try:
        hits = vector_store.search("documents", message, n_results=n_results)
    except Exception as e:
        logger.debug(f"[context/resolver] semantic search failed: {e}")
        return scores

    for h in hits:
        meta = h.get("metadata") or {}
        sid_raw = meta.get("space_id")
        if sid_raw is None:
            continue
        try:
            sid = int(sid_raw)
        except (TypeError, ValueError):
            continue
        dist = h.get("distance")
        if dist is None:
            relevance = 0.5
        else:
            relevance = max(0.0, 1.0 - float(dist))
        if relevance < MIN_SEMANTIC_SCORE:
            continue
        scores[sid] = scores.get(sid, 0) + relevance
    return scores


def _combine_scores(explicit: dict, semantic: dict) -> list:
    all_ids = set(explicit) | set(semantic)
    combined = []
    for sid in all_ids:
        e = explicit.get(sid, 0)
        s = semantic.get(sid, 0)
        # Explicit mention weighted heavily
        score = e * 2.0 + s
        space = context_store.get_space(sid)
        if not space:
            continue
        combined.append({
            "space_id": sid,
            "space_name": space["name"],
            "score": score,
            "explicit": e > 0,
            "semantic": s,
        })
    combined.sort(key=lambda x: x["score"], reverse=True)
    return combined


def resolve(message: str) -> dict:
    """
    Resolve which context space applies.

    Returns:
        {
            "chosen": {...space} or None,
            "candidates": [{space_id, space_name, score, explicit, semantic}, ...],
            "confidence": "high" | "low" | "none",
            "ambiguous": bool,
        }
    """
    explicit = _explicit_matches(message)
    semantic = _semantic_matches(message)
    candidates = _combine_scores(explicit, semantic)

    if not candidates:
        return {
            "chosen": None,
            "candidates": [],
            "confidence": "none",
            "ambiguous": False,
        }

    top = candidates[0]
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0
    margin = top["score"] - second_score

    # High confidence: strong explicit match OR clear semantic lead
    high = top["explicit"] or margin >= HIGH_CONFIDENCE_MARGIN
    ambiguous = len(candidates) > 1 and not high and top["score"] > 0

    chosen = None
    confidence = "none"
    if high and top["score"] > 0:
        chosen = context_store.get_space(top["space_id"])
        confidence = "high"
    elif top["score"] > 0 and not ambiguous:
        chosen = context_store.get_space(top["space_id"])
        confidence = "high"
    elif top["score"] > 0:
        confidence = "low"

    return {
        "chosen": chosen,
        "candidates": candidates[:5],
        "confidence": confidence,
        "ambiguous": ambiguous,
    }


def retrieve_context_chunks(message: str, space_id: int, k: int = 6) -> list:
    """Retrieve top chunks for a specific space."""
    try:
        hits = vector_store.search("documents", message, n_results=k * 3)
    except Exception:
        return []
    filtered = []
    for h in hits:
        meta = h.get("metadata") or {}
        if str(meta.get("space_id")) == str(space_id):
            filtered.append(h)
        if len(filtered) >= k:
            break
    return filtered


def build_context_block(message: str) -> str:
    """Build the context injection block for agent/core.py."""
    result = resolve(message)
    if result["confidence"] == "none":
        return ""

    if result["ambiguous"] or result["confidence"] == "low":
        names = ", ".join(c["space_name"] for c in result["candidates"][:4])
        return (
            f"[CONTEXT AMBIGUITY]\n"
            f"Multiple context spaces may apply to this message: {names}.\n"
            f"Ask the user which context they mean before proceeding with actions "
            f"that depend on project-specific knowledge."
        )

    space = result["chosen"]
    if not space:
        return ""

    chunks = retrieve_context_chunks(message, space["id"], k=6)
    lines = [
        f"[ACTIVE CONTEXT: {space['name']}]",
        space.get("description") or "",
    ]
    assets = context_store.list_assets(space["id"])
    ready = [a for a in assets if a.get("status") == "ready"]
    if ready:
        titles = ", ".join(
            (a.get("title") or a.get("url") or a.get("kind") or "?")[:40]
            for a in ready[:12]
        )
        lines.append(f"Assets in this space: {titles}")

    if chunks:
        lines.append("Relevant excerpts:")
        for h in chunks:
            src = (h.get("metadata") or {}).get("source", "?")
            lines.append(f"- [{src}] {h.get('text', '')[:400]}")

    return "\n".join(x for x in lines if x)

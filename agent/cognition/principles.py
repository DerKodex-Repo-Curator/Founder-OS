"""Principle storage, recall, and vector sync for LECE."""
import logging

from agent import store
from config import config

logger = logging.getLogger(__name__)

_embed = None


def _get_embedder():
    global _embed
    if _embed is not None:
        return _embed
    try:
        from chromadb.utils import embedding_functions
        _embed = embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        _embed = None
    return _embed


def _cosine(a, b):
    import numpy as np
    a, b = np.asarray(a, dtype="float32"), np.asarray(b, dtype="float32")
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def sync_to_vector(principle_id: int, principle: str, context: str = ""):
    try:
        from memory.vector_store import add as vec_add
        vec_add(
            "principles",
            f"{context}\nPrinciple: {principle}",
            metadata={"type": "principle", "id": principle_id},
            doc_id=f"principle_{principle_id}",
        )
    except Exception as e:
        logger.debug(f"[principles] vector sync skipped: {e}")


def find_similar_principle(text: str, threshold: float = 0.85) -> dict:
    """Semantic dedup via local embedder."""
    emb = _get_embedder()
    if emb is None:
        return {}
    try:
        q = emb([text[:500]])[0]
    except Exception:
        return {}
    best, best_score = None, 0.0
    for p in store.list_principles("active", 100):
        try:
            pv = emb([p["principle"][:500]])[0]
            s = _cosine(q, pv)
            if s > best_score:
                best_score, best = s, p
        except Exception:
            continue
    if best and best_score >= threshold:
        return {"principle": best, "score": best_score}
    return {}


def recall_for_turn(query: str, k: int = None) -> str:
    """Turn-level principle recall (global injection)."""
    if not getattr(config, "lece_enabled", True):
        return ""
    k = k or getattr(config, "lece_principles_k", 4)
    try:
        from memory.retrieval import hybrid_search
        hits = hybrid_search(query, collections=["principles"], k=k)
        if hits:
            return "\n".join(f"- {h['text'][:250]}" for h in hits)
    except Exception:
        pass
    rows = store.list_principles("active", k)
    if not rows:
        return ""
    return "\n".join(f"- {r['principle'][:250]}" for r in rows[:k])


def recall_for_step(state_text: str, k: int = 2) -> str:
    """Step-wise injection aligned to intermediate decision state."""
    if not getattr(config, "lece_enabled", True):
        return ""
    block = recall_for_turn(state_text, k=k)
    if not block:
        return ""
    return f"[STEP PRINCIPLES]\n{block}"

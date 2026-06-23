"""MASC-style metacognitive step anomaly detection via local embeddings."""
import logging

logger = logging.getLogger(__name__)

_embed = None
_embed_tried = False
_prototypes = {}  # role -> normalized vector


def _get_embedder():
    global _embed, _embed_tried
    if _embed_tried:
        return _embed
    _embed_tried = True
    try:
        from chromadb.utils import embedding_functions
        _embed = embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        _embed = None
    return _embed


def _normalize(v):
    import numpy as np
    a = np.asarray(v, dtype="float32")
    n = np.linalg.norm(a)
    return a / n if n else a


def _cosine(a, b):
    import numpy as np
    a, b = np.asarray(a, dtype="float32"), np.asarray(b, dtype="float32")
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def score_step(history_text: str, step_text: str, threshold: float = 0.25) -> dict:
    """Score whether step_text is anomalous given history. Lower score = more anomalous."""
    emb = _get_embedder()
    if emb is None or not step_text:
        return {"anomaly": False, "score": 1.0, "reason": "embedder_unavailable"}

    try:
        hist_vec = _normalize(emb([history_text or "start"])[0])
        step_vec = _normalize(emb([step_text[:800]])[0])
        score = _cosine(hist_vec, step_vec)
        anomaly = score < threshold
        return {
            "anomaly": anomaly,
            "score": round(score, 3),
            "reason": "low_causal_consistency" if anomaly else "ok",
        }
    except Exception as e:
        logger.debug(f"[healing/metacog] scoring failed: {e}")
        return {"anomaly": False, "score": 1.0, "reason": "scoring_error"}


def update_prototype(role: str, text: str):
    """Update normal-step prototype for a role."""
    emb = _get_embedder()
    if emb is None:
        return
    try:
        vec = _normalize(emb([text[:500]])[0])
        if role in _prototypes:
            import numpy as np
            _prototypes[role] = _normalize((_prototypes[role] + vec) / 2)
        else:
            _prototypes[role] = vec
    except Exception:
        pass

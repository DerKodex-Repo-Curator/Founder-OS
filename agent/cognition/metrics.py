"""LECE measurement metrics for evaluation and dashboard."""
import json

from agent import store


def preplay_accuracy(limit: int = 50) -> dict:
    rows = store.list_preplay_runs(limit)
    if not rows:
        return {"count": 0, "mae": 0.0, "accuracy": 0.0}
    errors = [abs(r.get("prediction_error") or 0) for r in rows]
    mae = sum(errors) / len(errors)
    accurate = sum(1 for e in errors if e < 0.3)
    return {
        "count": len(rows),
        "mae": round(mae, 3),
        "accuracy": round(accurate / len(rows), 3),
    }


def principle_effectiveness() -> dict:
    rows = store.list_principles("active", 100)
    if not rows:
        return {"count": 0, "avg_effectiveness": 0.0}
    eff = [r.get("effectiveness", 0) for r in rows]
    return {
        "count": len(rows),
        "avg_effectiveness": round(sum(eff) / len(eff), 3),
        "quarantined": len(store.list_principles("quarantined", 50)),
    }


def trust_summary() -> dict:
    scores = store.list_trust_scores(50)
    if not scores:
        return {"count": 0}
    comps = [s.get("competence", 0.5) for s in scores]
    return {
        "count": len(scores),
        "avg_competence": round(sum(comps) / len(comps), 3),
        "top": scores[:5],
    }


def distillation_history(limit: int = 10) -> list:
    return store.list_distill_runs(limit)


def autonomy_metrics() -> dict:
    """Proxy metrics for autonomy precision/recall."""
    approvals = store.list_pending_approvals()
    trust = store.list_trust_scores(30)
    high_trust = [t for t in trust if t.get("competence", 0) >= 0.8 and t.get("trials", 0) >= 5]
    return {
        "pending_approvals": len(approvals),
        "high_trust_actions": len(high_trust),
        "trust_scores": len(trust),
    }


def full_report() -> dict:
    return {
        "preplay": preplay_accuracy(),
        "principles": principle_effectiveness(),
        "trust": trust_summary(),
        "autonomy": autonomy_metrics(),
        "distillation": distillation_history(5),
    }

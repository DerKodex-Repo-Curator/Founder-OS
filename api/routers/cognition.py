"""LECE dashboard API endpoints."""
from fastapi import APIRouter

router = APIRouter(tags=["cognition"])


@router.get("/cognition")
def api_cognition():
    from agent.cognition.metrics import full_report
    from agent.cognition.workspace import render_state
    from agent.cognition.twin import twin_summary
    from agent import store
    return {
        "metrics": full_report(),
        "workspace": render_state(),
        "twin": twin_summary(),
        "principles": store.list_principles("active", 20),
        "distillation": store.list_distill_runs(10),
        "trust": store.list_trust_scores(20),
        "founder": store.get_founder_traits(),
    }

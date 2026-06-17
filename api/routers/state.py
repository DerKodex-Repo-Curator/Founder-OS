"""Dashboard state endpoint."""
from fastapi import APIRouter
from dashboard.state import collect_state

router = APIRouter(tags=["state"])


@router.get("/state")
def api_state():
    return collect_state()


@router.get("/health")
def health():
    """Lightweight health check for cloud deploys (AWS, Docker, uptime monitors)."""
    return {"status": "ok", "service": "founder-os-api"}

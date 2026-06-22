"""Job queue for distributed swarm workers."""
import json
import logging
import uuid
from datetime import datetime

from agent import store
from config import config

logger = logging.getLogger(__name__)


def enqueue_job(job_type: str, payload: dict, priority: int = 5) -> str:
    """Enqueue a swarm job. Returns job_id."""
    job_id = str(uuid.uuid4())[:16]
    mode = getattr(config, "swarm_worker_mode", "inproc")

    if mode == "redis":
        return _enqueue_redis(job_id, job_type, payload, priority)

    store.enqueue_swarm_job(job_id, job_type, json.dumps(payload, default=str), priority)
    return job_id


def _enqueue_redis(job_id: str, job_type: str, payload: dict, priority: int) -> str:
    try:
        import redis
        r = redis.from_url(getattr(config, "redis_url", "redis://localhost:6379/0"))
        r.zadd("swarm:jobs", {json.dumps({"id": job_id, "type": job_type, "payload": payload}): priority})
        return job_id
    except Exception as e:
        logger.warning(f"[queue] Redis unavailable, SQLite fallback: {e}")
        store.enqueue_swarm_job(job_id, job_type, json.dumps(payload, default=str), priority)
        return job_id


def dequeue_job() -> dict:
    mode = getattr(config, "swarm_worker_mode", "inproc")
    if mode == "redis":
        job = _dequeue_redis()
        if job:
            return job
    return store.dequeue_swarm_job()


def _dequeue_redis() -> dict:
    try:
        import redis
        r = redis.from_url(getattr(config, "redis_url", "redis://localhost:6379/0"))
        items = r.zpopmax("swarm:jobs", 1)
        if items:
            return json.loads(items[0][0])
    except Exception:
        pass
    return {}


def complete_job(job_id: str, result: str, status: str = "done"):
    store.finish_swarm_job(job_id, status, result[:4000])


async def run_job(job: dict) -> dict:
    """Execute a dequeued swarm job."""
    from agent.swarm.runner import run_swarm
    from agent.swarm.debate import run_debate
    from agent.swarm.mesh import run_mesh
    from agent.swarm.board import run_blackboard_round

    job_type = job.get("type", "swarm")
    payload = job.get("payload", {})
    goal = payload.get("goal", "")

    handlers = {
        "swarm": lambda: run_swarm(goal, payload.get("steps"), payload.get("topology")),
        "debate": lambda: run_debate(goal),
        "mesh": lambda: run_mesh(payload.get("artifact", ""), goal),
        "blackboard": lambda: run_blackboard_round(goal),
    }
    handler = handlers.get(job_type, handlers["swarm"])
    return await handler()

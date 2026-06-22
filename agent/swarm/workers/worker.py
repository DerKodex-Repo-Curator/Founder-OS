"""Swarm worker process — polls queue and executes jobs."""
import asyncio
import logging

from agent.swarm.workers.queue import dequeue_job, complete_job, run_job

logger = logging.getLogger(__name__)


async def worker_loop(poll_interval: float = 2.0, max_jobs: int = 100):
    """Poll the swarm job queue and execute jobs."""
    processed = 0
    while processed < max_jobs:
        job = dequeue_job()
        if not job:
            await asyncio.sleep(poll_interval)
            continue
        job_id = job.get("id", "unknown")
        try:
            result = await run_job(job)
            complete_job(job_id, str(result)[:4000], "done")
            logger.info(f"[worker] completed job {job_id}")
        except Exception as e:
            complete_job(job_id, str(e)[:500], "failed")
            logger.error(f"[worker] job {job_id} failed: {e}")
        processed += 1


def start_worker_background():
    """Start worker loop as asyncio task (for in-process mode)."""
    return asyncio.create_task(worker_loop())

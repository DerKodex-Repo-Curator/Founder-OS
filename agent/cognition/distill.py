"""Principle-level self-distillation from lived traces (Tier A)."""
import json
import logging

from agent import store
from agent.cognition import episodes as ep_mod
from agent.cognition.principles import find_similar_principle, sync_to_vector
from config import config
from llm.router import complete

logger = logging.getLogger(__name__)

DECAY_FACTOR = 0.98
QUARANTINE_THRESHOLD = 0.2


async def extract_principles_from_cluster(cluster: list) -> list:
    """LLM extraction of durable principles from similar episodes."""
    if not cluster:
        return []
    samples = []
    for ep in cluster[:8]:
        samples.append(
            f"Task: {ep.get('message','')[:200]}\n"
            f"Tools: {', '.join(ep.get('tools') or [])}\n"
            f"Outcome preview: {ep.get('result_preview','')[:150]}\n"
            f"Score: {ep.get('score', 0):.2f}"
        )
    prompt = [
        {"role": "system", "content":
            "You distill PRINCIPLE-LEVEL experience from founder-agent interaction episodes. "
            "Extract durable, transferable strategies — NOT instance-specific details. "
            "Respond ONLY with JSON: {\"principles\": [{\"principle\": \"...\", \"context\": \"...\"}]}"},
        {"role": "user", "content": "EPISODES:\n" + "\n---\n".join(samples)},
    ]
    try:
        raw = await complete(prompt, task_type="analysis", max_tokens=600)
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return data.get("principles") or []
    except Exception as e:
        logger.debug(f"[distill] extract failed: {e}")
        return []


def _cluster_episodes(eps: list) -> list:
    """Simple tool-name clustering when embedder unavailable."""
    buckets = {}
    for ep in eps:
        key = (ep.get("tools") or ["general"])[0] or "general"
        buckets.setdefault(key, []).append(ep)
    return list(buckets.values())


async def run_distillation(since_ts: float = 0.0, limit: int = 100) -> dict:
    """Main distillation pass: episodes -> principles with dedup + decay."""
    if not getattr(config, "lece_enabled", True):
        return {"skipped": True, "reason": "LECE disabled"}
    if not getattr(config, "lece_distill_enabled", True):
        return {"skipped": True, "reason": "distillation disabled"}

    run_id = store.create_distill_run()
    eps = ep_mod.load_episodes(since_ts=since_ts, limit=limit, off_policy_only=True)
    eps += ep_mod.episodes_from_action_log(30)
    clusters = _cluster_episodes(eps)

    added, updated = 0, 0
    trace_ids = []

    for cluster in clusters:
        if not cluster:
            continue
        avg_score = sum(e.get("score", 0.5) for e in cluster) / len(cluster)
        extracted = await extract_principles_from_cluster(cluster)
        for item in extracted:
            principle = (item.get("principle") or "").strip()
            context = (item.get("context") or "").strip()
            if not principle or len(principle) < 10:
                continue
            for ep in cluster:
                tid = ep.get("trace_id")
                if tid:
                    trace_ids.append(tid)
            dup = find_similar_principle(principle)
            if dup:
                p = dup["principle"]
                new_support = p["support"] + 1
                new_rate = (p["success_rate"] * p["support"] + avg_score) / new_support
                new_eff = p["effectiveness"] * DECAY_FACTOR + avg_score * (1 - DECAY_FACTOR)
                status = "quarantined" if new_eff < QUARANTINE_THRESHOLD else "active"
                store.update_principle(
                    p["id"], support=new_support, success_rate=new_rate,
                    effectiveness=new_eff, status=status,
                )
                updated += 1
            else:
                pid = store.add_principle(
                    principle, context=context,
                    trace_ids=",".join(set(trace_ids))[:500],
                    support=len(cluster), success_rate=avg_score,
                    effectiveness=avg_score,
                )
                sync_to_vector(pid, principle, context)
                added += 1

    # Decay existing principles not reinforced
    for p in store.list_principles("active", 200):
        new_eff = p["effectiveness"] * DECAY_FACTOR
        if new_eff < QUARANTINE_THRESHOLD:
            store.quarantine_principle(p["id"])
        else:
            store.update_principle(p["id"], effectiveness=new_eff)

    detail = f"processed {len(eps)} episodes in {len(clusters)} clusters"
    store.finish_distill_run(run_id, len(eps), added, updated, detail=detail)

    result = {"run_id": run_id, "episodes": len(eps), "added": added, "updated": updated}

    if getattr(config, "lece_distill_train", False):
        try:
            from agent.cognition.train import gate as train_gate
            train_result = await train_gate.maybe_train_and_promote(eps)
            result["train"] = train_result
        except Exception as e:
            result["train"] = {"skipped": True, "error": str(e)[:200]}

    from agent.cognition.manual import rebuild_manual
    rebuild_manual()

    return result

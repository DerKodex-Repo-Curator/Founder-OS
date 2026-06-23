"""Preplay: simulate before acting on high-stakes decisions."""
import json
import logging

from agent import critic, subagent
from agent.cognition import twin, sandbox
from agent import store, trace
from config import config

logger = logging.getLogger(__name__)

HIGH_STAKES = sandbox.WRITE_TOOLS | {
    "send_email", "x_post", "calendar_delete_event", "create_tool",
}


def needs_preplay(tool_name: str) -> bool:
    if not getattr(config, "lece_enabled", True):
        return False
    if not getattr(config, "lece_preplay_enabled", True):
        return False
    return tool_name in HIGH_STAKES


def _generate_candidates(tool_name: str, args: dict, n: int = 3) -> list:
    """Generate candidate action variants."""
    base = {"tool": tool_name, "args": args, "label": "baseline"}
    candidates = [base]
    if tool_name == "send_email":
        candidates.append({
            "tool": tool_name,
            "args": {**args, "subject": (args.get("subject") or "") + " (follow-up)"},
            "label": "follow_up_subject",
        })
        candidates.append({
            "tool": tool_name,
            "args": {**args, "body": (args.get("body") or "")[:500] + "\n\nWould love your thoughts."},
            "label": "softer_close",
        })
    while len(candidates) < n:
        candidates.append({**base, "label": f"variant_{len(candidates)}"})
    return candidates[:n]


async def _estimate_learned(candidate: dict, state: dict) -> dict:
    pred = twin.predict_outcome(state, candidate["tool"], candidate.get("args"))
    return {**candidate, "score": pred.get("confidence", 0.5), "prediction": pred}


async def _estimate_swarm(candidates: list, state_text: str, goal: str) -> list:
    """LLM rollout estimation via parallel sub-agents in sandbox."""
    tasks = []
    for i, c in enumerate(candidates):
        task = (
            f"SIMULATION (no real actions). Twin state:\n{state_text}\n\n"
            f"Candidate {i}: tool={c['tool']} label={c.get('label','')}\n"
            f"Args: {json.dumps(c.get('args', {}), default=str)[:400]}\n\n"
            f"Predict the likely outcome for the founder's business. Be concise."
        )
        tasks.append({"specialist": "analyst", "task": task})
    with sandbox.SimulationContext():
        results = await subagent.run_parallel(tasks)
    scored = []
    for c, r in zip(candidates, results):
        text = r.get("result", "")
        score = 0.6
        if any(w in text.lower() for w in ("positive", "success", "likely", "good")):
            score = 0.75
        if any(w in text.lower() for w in ("risk", "fail", "unlikely", "bad")):
            score = 0.35
        scored.append({**c, "score": score, "rollout": text[:300]})
    return scored


async def run_preplay(tool_name: str, args: dict, goal: str = "") -> dict:
    """Run full preplay and return best candidate + metadata."""
    state = twin.build_state_vector()
    state_text = twin.snapshot_for_preplay()
    n = getattr(config, "lece_preplay_branches", 3)
    mode = getattr(config, "lece_preplay_mode", "hybrid")
    candidates = _generate_candidates(tool_name, args, n)

    if mode == "learned":
        scored = [await _estimate_learned(c, state) for c in candidates]
    elif mode == "swarm":
        scored = await _estimate_swarm(candidates, state_text, goal)
    else:
        learned = [await _estimate_learned(c, state) for c in candidates]
        if max(c.get("score", 0) for c in learned) < 0.55:
            scored = await _estimate_swarm(candidates, state_text, goal)
        else:
            scored = learned

    best_idx = max(range(len(scored)), key=lambda i: scored[i].get("score", 0))
    best = scored[best_idx]

    tid = ""
    t = trace.current()
    if t:
        tid = t.id

    store.log_preplay_run(
        tid, tool_name, json.dumps(scored, default=str)[:4000],
        best_idx, str(best.get("prediction", best.get("rollout", "")))[:500],
        mode=mode,
    )
    return {
        "selected_idx": best_idx,
        "candidate": best,
        "candidates": scored,
        "mode": mode,
    }


async def maybe_preplay(tool_name: str, args: dict, goal: str = "") -> dict:
    """Gate: run preplay if enabled and tool is high-stakes."""
    if not needs_preplay(tool_name):
        return {"skipped": True, "tool": tool_name}
    try:
        return await run_preplay(tool_name, args, goal)
    except Exception as e:
        logger.warning(f"[preplay] failed: {e}")
        return {"skipped": True, "error": str(e)[:200]}


def record_actual_outcome(tool_name: str, args: dict, result, preplay_id: int = None):
    """Closed loop: update twin transition reliabilities."""
    result_str = result if isinstance(result, str) else json.dumps(result, default=str)
    success = "error" not in result_str.lower() and "fail" not in result_str.lower()
    twin.record_transition(tool_name, args, result_str[:200], success)
    if preplay_id:
        rows = store.list_preplay_runs(1)
        if rows:
            pred = rows[0].get("predicted_outcome", "")
            err = 0.0 if success and "success" in pred.lower() else 0.5
            if not success:
                err = 1.0
            store.log_preplay_run(
                rows[0].get("trace_id", ""), tool_name,
                rows[0].get("candidates_json", ""), rows[0].get("selected_idx", 0),
                pred, result_str[:500], err, rows[0].get("mode", ""),
            )

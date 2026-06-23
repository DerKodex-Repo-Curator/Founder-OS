"""Trace segmentation and outcome scoring for LECE distillation."""
import json
import logging
import re

from agent import trace, store

logger = logging.getLogger(__name__)

_SUCCESS_HINTS = re.compile(
    r"\b(success|completed|sent|done|approved|executed|positive|reply|booked)\b", re.I
)
_FAIL_HINTS = re.compile(
    r"\b(fail|error|denied|rejected|timeout|stuck|wrong|invalid)\b", re.I
)


def segment_trace(rec: dict) -> list:
    """Split one trace into tool-level episodes."""
    episodes = []
    base = {
        "trace_id": rec.get("id", ""),
        "actor": rec.get("actor", ""),
        "message": rec.get("message", "")[:500],
        "final": rec.get("final", "")[:500],
        "ts": rec.get("ts", 0),
    }
    tool_events = [e for e in rec.get("events", []) if e.get("type") == "tool"]
    if not tool_events:
        episodes.append({**base, "tools": [], "kind": "turn"})
        return episodes
    for ev in tool_events:
        data = ev.get("data") or {}
        episodes.append({
            **base,
            "tools": [data.get("name", "")],
            "decision": data.get("decision", ""),
            "args": data.get("args") or {},
            "result_preview": data.get("result_preview", "")[:300],
            "kind": "tool",
        })
    return episodes


def score_episode(ep: dict) -> float:
    """Local reward model: 0..1 outcome quality from existing signals."""
    score = 0.5
    preview = ep.get("result_preview", "") + " " + ep.get("final", "")
    if _SUCCESS_HINTS.search(preview):
        score += 0.25
    if _FAIL_HINTS.search(preview):
        score -= 0.35
    if ep.get("decision") == "allow":
        score += 0.05
    if ep.get("decision") == "deny":
        score -= 0.2
    healing = [e for e in (ep.get("_events") or []) if e.get("type") == "healing"]
    if healing:
        score -= 0.15 * len(healing)
    return max(0.0, min(1.0, score))


def load_episodes(since_ts: float = 0.0, limit: int = 200,
                  off_policy_only: bool = True, min_score: float = 0.6) -> list:
    """Load scored episodes from traces, optionally off-policy filtered."""
    traces = trace.iter_traces(since_ts=since_ts, limit=limit)
    episodes = []
    for rec in traces:
        for ep in segment_trace(rec):
            ep["_events"] = rec.get("events", [])
            ep["score"] = score_episode(ep)
            if off_policy_only and ep["score"] < min_score:
                continue
            episodes.append(ep)
    return episodes


def episodes_from_action_log(limit: int = 50) -> list:
    """Supplement trace episodes with action_log outcomes."""
    rows = store.recent_actions(limit)
    out = []
    for r in rows:
        result = r.get("result") or ""
        score = 0.7 if _SUCCESS_HINTS.search(result) else 0.3
        if _FAIL_HINTS.search(result):
            score = 0.2
        out.append({
            "trace_id": "",
            "actor": r.get("actor", ""),
            "message": "",
            "tools": [r.get("tool_name", "")],
            "result_preview": result[:300],
            "score": score,
            "kind": "action_log",
        })
    return out

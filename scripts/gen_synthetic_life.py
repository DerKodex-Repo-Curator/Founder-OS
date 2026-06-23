"""Reproducible synthetic founder-life trace generator for LECE evals."""
import json
import os
import random
import time
import uuid

OUT_DIR = "./data/traces/synthetic"


def _tool_event(name, decision="allow", preview="success"):
    return {
        "t": round(random.uniform(0.5, 5.0), 2),
        "type": "tool",
        "data": {
            "name": name,
            "decision": decision,
            "args": {},
            "result_preview": preview,
        },
    }


def generate_trace(day_offset: int = 0, scenario: str = "outreach") -> dict:
    ts = time.time() - day_offset * 86400
    tid = uuid.uuid4().hex[:12]
    scenarios = {
        "outreach": {
            "message": "Research and draft outreach to 3 SaaS founders",
            "final": "Drafted 3 personalized emails; queued for approval.",
            "events": [
                _tool_event("web_search", preview="found 5 results success"),
                _tool_event("add_contact", preview="contact added success"),
                _tool_event("send_email", decision="approve", preview="pending approval"),
            ],
        },
        "fundraising": {
            "message": "Update investor pipeline and schedule follow-ups",
            "final": "Pipeline updated; 2 follow-ups scheduled.",
            "events": [
                _tool_event("search_memory", preview="recalled prior meetings"),
                _tool_event("set_followup", preview="follow-up set success"),
            ],
        },
        "failure": {
            "message": "Post product update to X",
            "final": "Could not complete — API error.",
            "events": [
                _tool_event("x_post", preview="error rate limit failed"),
            ],
        },
    }
    s = scenarios.get(scenario, scenarios["outreach"])
    return {
        "id": tid,
        "actor": "user",
        "message": s["message"],
        "final": s["final"],
        "duration_s": round(random.uniform(3, 30), 1),
        "ts": ts,
        "events": s["events"],
        "synthetic": True,
    }


def generate_dataset(n_days: int = 14, traces_per_day: int = 5) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "synthetic_life.jsonl")
    scenarios = ["outreach", "fundraising", "failure"]
    with open(path, "w", encoding="utf-8") as f:
        for day in range(n_days):
            for _ in range(traces_per_day):
                sc = random.choice(scenarios)
                rec = generate_trace(day_offset=day, scenario=sc)
                f.write(json.dumps(rec) + "\n")
    return path


if __name__ == "__main__":
    p = generate_dataset()
    print(f"Generated synthetic life dataset: {p}")

"""LECE evaluation scenarios and ablation harness."""
import asyncio

SCENARIOS = [
    {
        "id": "lece_principle_recall",
        "description": "Principles should be recallable for outreach context",
        "query": "draft investor outreach email",
        "expect_tools": [],
    },
    {
        "id": "lece_preplay_routing",
        "description": "High-stakes send_email should trigger preplay path",
        "query": "send a follow-up email to the lead we met yesterday",
        "expect_tools": ["preplay_action", "send_email"],
    },
    {
        "id": "lece_twin_state",
        "description": "Agent can inspect digital twin state",
        "query": "what does our business twin look like right now?",
        "expect_tools": ["twin_state"],
    },
]

ABLATIONS = [
    {"name": "principle_vs_instance", "principle_level": True, "instance_level": False},
    {"name": "step_wise_vs_global", "step_wise": True, "global_only": False},
    {"name": "off_policy_vs_on_policy", "off_policy": True, "min_score": 0.6},
    {"name": "preplay_on", "preplay_enabled": True},
    {"name": "preplay_off", "preplay_enabled": False},
    {"name": "adaptive_autonomy_on", "adaptive_autonomy": True},
    {"name": "adaptive_autonomy_off", "adaptive_autonomy": False},
]


async def run_ablation(name: str, config_overrides: dict = None) -> dict:
    """Run a single ablation config and return proxy metrics."""
    from agent.cognition.metrics import full_report
    from agent.cognition import episodes as ep_mod

    config_overrides = config_overrides or {}
    eps = ep_mod.load_episodes(limit=50, off_policy_only=config_overrides.get("off_policy", True),
                               min_score=config_overrides.get("min_score", 0.6))
    report = full_report()
    return {
        "ablation": name,
        "episodes_loaded": len(eps),
        "metrics": report,
        "config": config_overrides,
    }


def list_scenarios():
    return SCENARIOS


def list_ablations():
    return ABLATIONS

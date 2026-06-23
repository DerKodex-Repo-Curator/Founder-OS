"""Simulation sandbox: copy-on-write shadow store for preplay."""
import contextvars
import copy
import json
import logging

logger = logging.getLogger(__name__)

SIMULATION = contextvars.ContextVar("simulation", default=False)
_shadow_writes: contextvars.ContextVar = contextvars.ContextVar("shadow_writes", default=None)

# Tools that mutate external/world state — intercepted in simulation.
WRITE_TOOLS = {
    "send_email", "x_post", "calendar_create_event", "calendar_delete_event",
    "add_contact", "update_contact_status", "set_followup", "add_task",
    "calendar_create_event", "set_reminder", "add_goal", "graph_link",
    "create_tool", "propose_code_change",
}


def is_simulation() -> bool:
    return bool(SIMULATION.get())


def enter_simulation():
    """Context manager entry — set simulation flag and empty shadow."""
    token_sim = SIMULATION.set(True)
    token_shadow = _shadow_writes.set({})
    return token_sim, token_shadow


def exit_simulation(tokens):
    token_sim, token_shadow = tokens
    SIMULATION.reset(token_sim)
    _shadow_writes.reset(token_shadow)


class SimulationContext:
    def __enter__(self):
        self.tokens = enter_simulation()
        return self

    def __exit__(self, *args):
        exit_simulation(self.tokens)


def shadow_write(key: str, value):
    writes = _shadow_writes.get()
    if writes is None:
        writes = {}
        _shadow_writes.set(writes)
    writes[key] = copy.deepcopy(value)


def shadow_read(key: str, default=None):
    writes = _shadow_writes.get() or {}
    return writes.get(key, default)


def simulate_tool_result(tool_name: str, args: dict, prediction: dict = None) -> dict:
    """Return predicted result without executing the real tool."""
    pred = prediction or {}
    return {
        "simulated": True,
        "tool": tool_name,
        "args_preview": {k: str(v)[:100] for k, v in (args or {}).items()},
        "predicted_outcome": pred.get("predicted", "success"),
        "confidence": pred.get("confidence", 0.5),
        "message": f"[SIMULATION] {tool_name} would run with predicted outcome: "
                   f"{pred.get('predicted', 'success')} (conf={pred.get('confidence', 0.5):.0%})",
    }


def should_intercept(tool_name: str) -> bool:
    return is_simulation() and tool_name in WRITE_TOOLS

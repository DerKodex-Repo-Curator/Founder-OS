"""Self-healing tool router — route around failed tools without an LLM call."""
import logging

from agent.healing import circuit
from agent.healing.fallback import substitute_tool

logger = logging.getLogger(__name__)

# In-memory blocked tools for this process (infinite weight)
_BLOCKED = set()


def block_tool(tool_name: str):
    """Mark a tool as blocked (infinite weight) for routing."""
    _BLOCKED.add(tool_name)
    circuit.record_failure(f"tool:{tool_name}")


def unblock_tool(tool_name: str):
    _BLOCKED.discard(tool_name)
    circuit.record_success(f"tool:{tool_name}")


def is_blocked(tool_name: str) -> bool:
    if tool_name in _BLOCKED:
        return True
    if not circuit.allow_call(f"tool:{tool_name}"):
        return True
    return False


def route_around(failed_tool: str) -> str:
    """Return an alternative tool that is not blocked, or empty string."""
    alt = substitute_tool(failed_tool)
    if alt and not is_blocked(alt):
        logger.info(f"[healing/router] routing {failed_tool} -> {alt}")
        return alt
    # Try any substitute not blocked
    from agent.healing.fallback import _SUBSTITUTIONS
    for candidate in _SUBSTITUTIONS.get(failed_tool, []):
        if candidate and not is_blocked(candidate):
            return candidate
    return ""


def clear_blocks():
    _BLOCKED.clear()

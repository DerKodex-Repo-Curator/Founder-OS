"""Failure diagnosis — classify errors into the healing taxonomy."""
import json
import logging
import re

from agent.healing.taxonomy import FailureClass

logger = logging.getLogger(__name__)

_RATE_LIMIT = re.compile(r"rate.?limit|429|too many requests", re.I)
_TIMEOUT = re.compile(r"timeout|timed out|deadline", re.I)
_BAD_ARGS = re.compile(r"bad arguments|typeerror|missing required|invalid.*argument", re.I)
_BUDGET = re.compile(r"budget|cap reached|paused", re.I)
_CIRCUIT = re.compile(r"circuit.*open", re.I)


def diagnose_exception(exc: Exception, kind: str = "tool") -> FailureClass:
    msg = str(exc or "")
    if _BUDGET.search(msg):
        return FailureClass.BUDGET
    if _CIRCUIT.search(msg):
        return FailureClass.CIRCUIT_OPEN
    if _RATE_LIMIT.search(msg):
        return FailureClass.RATE_LIMIT
    if _TIMEOUT.search(msg):
        return FailureClass.TIMEOUT
    if _BAD_ARGS.search(msg):
        return FailureClass.MALFORMED_ARGS
    if kind == "llm":
        return FailureClass.TRANSIENT
    return FailureClass.TOOL_EXCEPTION


def diagnose_result(result, tool_name: str = "") -> FailureClass:
    """Classify a tool result dict that indicates failure."""
    if result is None:
        return FailureClass.EMPTY_RESULT
    if isinstance(result, str):
        if not result.strip():
            return FailureClass.EMPTY_RESULT
        return FailureClass.UNKNOWN
    if not isinstance(result, dict):
        return FailureClass.UNKNOWN

    if result.get("denied"):
        return FailureClass.UNKNOWN  # policy, not healable
    err = str(result.get("error", ""))
    if not err:
        if result.get("error") is None and len(result) == 0:
            return FailureClass.EMPTY_RESULT
        return FailureClass.UNKNOWN  # success

    if "unknown tool" in err.lower():
        return FailureClass.WRONG_TOOL
    if _BAD_ARGS.search(err):
        return FailureClass.MALFORMED_ARGS
    if _TIMEOUT.search(err):
        return FailureClass.TIMEOUT
    if _RATE_LIMIT.search(err):
        return FailureClass.RATE_LIMIT
    if "empty" in err.lower() or "no results" in err.lower():
        return FailureClass.EMPTY_RESULT
    return FailureClass.TOOL_EXCEPTION


def is_failure(result, exc: Exception = None) -> bool:
    if exc is not None:
        return True
    if isinstance(result, dict) and result.get("error"):
        return True
    if isinstance(result, dict) and result.get("denied"):
        return False
    return False


def signal_text(result, exc: Exception = None) -> str:
    if exc is not None:
        return str(exc)[:500]
    if isinstance(result, dict):
        return json.dumps(result, default=str)[:500]
    return str(result)[:500]

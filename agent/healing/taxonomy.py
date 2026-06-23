"""Failure taxonomy for self-healing diagnosis."""
from enum import Enum


class FailureClass(str, Enum):
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    MALFORMED_ARGS = "malformed_args"
    WRONG_TOOL = "wrong_tool"
    EMPTY_RESULT = "empty_result"
    SEMANTIC_INCONSISTENCY = "semantic_inconsistency"
    HALLUCINATION = "hallucination"
    TOOL_EXCEPTION = "tool_exception"
    BUDGET = "budget"
    CIRCUIT_OPEN = "circuit_open"
    STUCK_LOOP = "stuck_loop"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    RETRY = "retry"
    BACKOFF_RETRY = "backoff_retry"
    ARG_REPAIR = "arg_repair"
    TOOL_SUBSTITUTE = "tool_substitute"
    FALLBACK_PROVIDER = "fallback_provider"
    ROUTE_AROUND = "route_around"
    REFLECT = "reflect"
    REPLAN = "replan"
    ROLLBACK = "rollback"
    COMPENSATE = "compensate"
    DEGRADE = "degrade"
    ESCALATE = "escalate"
    ABORT = "abort"

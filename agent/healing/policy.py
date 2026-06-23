"""Recovery-budget control policy — maps failure class to ordered recovery actions."""
from agent.healing.taxonomy import FailureClass, RecoveryAction

# Priority: cheap local repairs first, expensive global recovery last.
_POLICY = {
    FailureClass.TRANSIENT: [
        RecoveryAction.BACKOFF_RETRY, RecoveryAction.FALLBACK_PROVIDER, RecoveryAction.DEGRADE,
    ],
    FailureClass.RATE_LIMIT: [
        RecoveryAction.BACKOFF_RETRY, RecoveryAction.FALLBACK_PROVIDER, RecoveryAction.DEGRADE,
    ],
    FailureClass.TIMEOUT: [
        RecoveryAction.BACKOFF_RETRY, RecoveryAction.TOOL_SUBSTITUTE, RecoveryAction.DEGRADE,
    ],
    FailureClass.MALFORMED_ARGS: [
        RecoveryAction.ARG_REPAIR, RecoveryAction.RETRY, RecoveryAction.REFLECT,
    ],
    FailureClass.WRONG_TOOL: [
        RecoveryAction.TOOL_SUBSTITUTE, RecoveryAction.ROUTE_AROUND, RecoveryAction.REFLECT,
    ],
    FailureClass.EMPTY_RESULT: [
        RecoveryAction.TOOL_SUBSTITUTE, RecoveryAction.RETRY, RecoveryAction.DEGRADE,
    ],
    FailureClass.TOOL_EXCEPTION: [
        RecoveryAction.BACKOFF_RETRY, RecoveryAction.TOOL_SUBSTITUTE, RecoveryAction.ROUTE_AROUND,
    ],
    FailureClass.CIRCUIT_OPEN: [
        RecoveryAction.ROUTE_AROUND, RecoveryAction.TOOL_SUBSTITUTE, RecoveryAction.FALLBACK_PROVIDER,
    ],
    FailureClass.SEMANTIC_INCONSISTENCY: [
        RecoveryAction.REFLECT, RecoveryAction.REPLAN, RecoveryAction.DEGRADE,
    ],
    FailureClass.HALLUCINATION: [
        RecoveryAction.REFLECT, RecoveryAction.ROLLBACK, RecoveryAction.ESCALATE,
    ],
    FailureClass.STUCK_LOOP: [
        RecoveryAction.REFLECT, RecoveryAction.REPLAN, RecoveryAction.ABORT,
    ],
    FailureClass.BUDGET: [
        RecoveryAction.DEGRADE, RecoveryAction.ABORT,
    ],
    FailureClass.UNKNOWN: [
        RecoveryAction.RETRY, RecoveryAction.REFLECT, RecoveryAction.DEGRADE, RecoveryAction.ESCALATE,
    ],
}


def recovery_actions(failure_class: FailureClass, budget_remaining: int) -> list:
    """Return ordered recovery actions, capped by remaining budget."""
    actions = list(_POLICY.get(failure_class, _POLICY[FailureClass.UNKNOWN]))
    if budget_remaining <= 0:
        return [RecoveryAction.DEGRADE, RecoveryAction.ABORT]
    return actions[:budget_remaining + 1]

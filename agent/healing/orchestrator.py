"""Self-healing orchestrator — monitor/detect/diagnose/recover/verify control plane."""
import logging
import time

from config import config
from agent import trace
from agent.healing.taxonomy import FailureClass, RecoveryAction
from agent.healing import diagnose, circuit, policy, ledger, escalate
from agent.healing.retry import retry_async, backoff_delay
from agent.healing.fallback import substitute_tool
from agent.healing.repair import repair_args
from agent.healing.router import route_around, block_tool, is_blocked
from agent.healing import metacog

logger = logging.getLogger(__name__)


class RecoveryBudget:
    """Per-turn recovery budget tracker."""

    def __init__(self, max_recoveries: int = None):
        self.max = max_recoveries or getattr(config, "healing_max_recoveries", 4)
        self.used = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max - self.used)

    def consume(self):
        self.used += 1

    def exhausted(self) -> bool:
        return self.used >= self.max


# Module-level budget for current turn (set by loop)
_current_budget: RecoveryBudget = None


def healing_enabled() -> bool:
    return getattr(config, "healing_enabled", True)


def set_budget(budget: RecoveryBudget):
    global _current_budget
    _current_budget = budget


def get_budget() -> RecoveryBudget:
    global _current_budget
    if _current_budget is None:
        _current_budget = RecoveryBudget()
    return _current_budget


def _log_healing_event(step: int, failure_class: str, action: str, outcome: str, cost_ms: int = 0):
    try:
        from agent import store
        tid = ""
        t = trace.current()
        if t:
            tid = t.id
        store.log_healing_event(tid, step, failure_class, action, outcome, cost_ms)
        trace.add("healing", {"failure_class": failure_class, "action": action, "outcome": outcome})
    except Exception:
        pass


async def heal_call(fn, kind: str = "tool", ctx: dict = None):
    """Wrap any async callable through the healing control plane.

    fn: async callable with no args that performs the operation.
    kind: 'tool' | 'llm'
    ctx: {tool_name, args, actor, step, circuit_key}
    """
    if not healing_enabled():
        return await fn()

    ctx = ctx or {}
    budget = get_budget()
    circuit_key = ctx.get("circuit_key") or f"{kind}:{ctx.get('tool_name', 'llm')}"
    tool_name = ctx.get("tool_name", "")
    args = ctx.get("args") or {}
    actor = ctx.get("actor", "agent")
    step = ctx.get("step", 0)

    # Fast-fail if circuit open
    if not circuit.allow_call(circuit_key):
        fc = FailureClass.CIRCUIT_OPEN
        alt = route_around(tool_name) if tool_name else ""
        if alt and budget.remaining > 0:
            budget.consume()
            _log_healing_event(step, fc.value, RecoveryAction.ROUTE_AROUND.value, f"routed_to:{alt}")
            return {"_healed": True, "_substitute": alt, "_original": tool_name}

    t0 = time.time()
    last_exc = None
    last_result = None

    try:
        result = await retry_async(fn, label=circuit_key)
        if isinstance(result, dict) and result.get("error") and not result.get("_healed"):
            last_result = result
            fc = diagnose.diagnose_result(result, tool_name)
            signal = diagnose.signal_text(result)
        else:
            circuit.record_success(circuit_key)
            return result
    except Exception as e:
        last_exc = e
        fc = diagnose.diagnose_exception(e, kind)
        signal = diagnose.signal_text(None, last_exc)

    if last_result is None and last_exc is None:
        fc = FailureClass.UNKNOWN
        signal = "unknown failure"
    actions = policy.recovery_actions(fc, budget.remaining)

    for action in actions:
        if budget.exhausted():
            break
        budget.consume()
        cost_ms = int((time.time() - t0) * 1000)

        try:
            if action == RecoveryAction.BACKOFF_RETRY:
                import asyncio
                await asyncio.sleep(backoff_delay(budget.used))
                result = await fn()
                circuit.record_success(circuit_key)
                ledger.record_failure(actor, kind, fc.value, signal, tool_name,
                                      recovery_action=action.value, recovered=True)
                _log_healing_event(step, fc.value, action.value, "recovered", cost_ms)
                return result

            elif action == RecoveryAction.ARG_REPAIR and tool_name:
                fixed_args = repair_args(tool_name, args, signal)
                if fixed_args != args:
                    from agent import registry
                    result = await registry.call(tool_name, fixed_args)
                    if not diagnose.is_failure(result):
                        circuit.record_success(circuit_key)
                        ledger.record_failure(actor, kind, fc.value, signal, tool_name,
                                              recovery_action=action.value, recovered=True)
                        _log_healing_event(step, fc.value, action.value, "recovered", cost_ms)
                        return result

            elif action == RecoveryAction.TOOL_SUBSTITUTE and tool_name:
                alt = substitute_tool(tool_name)
                if alt and not is_blocked(alt):
                    from agent import registry
                    result = await registry.call(alt, args)
                    if not diagnose.is_failure(result):
                        _log_healing_event(step, fc.value, action.value, f"substituted:{alt}", cost_ms)
                        return result

            elif action == RecoveryAction.ROUTE_AROUND and tool_name:
                alt = route_around(tool_name)
                if alt:
                    from agent import registry
                    result = await registry.call(alt, args)
                    _log_healing_event(step, fc.value, action.value, f"routed:{alt}", cost_ms)
                    return result

            elif action == RecoveryAction.DEGRADE:
                msg = escalate.degrade(reason=signal)
                _log_healing_event(step, fc.value, action.value, "degraded", cost_ms)
                ledger.record_failure(actor, kind, fc.value, signal, tool_name,
                                      recovery_action=action.value, recovered=False)
                return {"error": signal, "_degraded_response": msg}

            elif action == RecoveryAction.ESCALATE:
                esc = await escalate.escalate_to_founder(
                    f"Failed {kind} `{tool_name}` after recovery attempts.",
                    diagnosis=f"{fc.value}: {signal[:200]}",
                )
                _log_healing_event(step, fc.value, action.value, "escalated", cost_ms)
                return {"error": signal, "_escalated": esc}

        except Exception as recovery_exc:
            logger.debug(f"[healing] recovery action {action} failed: {recovery_exc}")
            continue

    # All recovery exhausted
    circuit.record_failure(circuit_key)
    if tool_name:
        block_tool(tool_name)
    ledger.record_failure(actor, kind, fc.value, signal, tool_name, recovered=False)
    _log_healing_event(step, fc.value, "exhausted", "failed", int((time.time() - t0) * 1000))

    if last_exc:
        raise last_exc
    return last_result or {"error": signal}


def detect_stuck_loop(recent_calls: list, threshold: int = 3) -> bool:
    """Detect if the agent is repeating the same failing call."""
    if len(recent_calls) < threshold:
        return False
    tail = recent_calls[-threshold:]
    if len(set(tail)) == 1:
        return True
    return False

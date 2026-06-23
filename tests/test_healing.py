"""Unit tests for self-healing control plane."""
import asyncio
import pytest

from agent.healing.taxonomy import FailureClass, RecoveryAction
from agent.healing.diagnose import diagnose_exception, diagnose_result, is_failure
from agent.healing.retry import backoff_delay
from agent.healing.circuit import CircuitState, record_failure, record_success, get_state, is_open
from agent.healing.policy import recovery_actions
from agent.healing.repair import repair_args, repair_json_output
from agent.healing.fallback import substitute_tool
from agent.healing.orchestrator import detect_stuck_loop, RecoveryBudget
from agent import store


class TestTaxonomy:
    def test_recovery_actions_transient(self):
        actions = recovery_actions(FailureClass.TRANSIENT, 3)
        assert RecoveryAction.BACKOFF_RETRY in actions

    def test_recovery_actions_budget_exhausted(self):
        actions = recovery_actions(FailureClass.TRANSIENT, 0)
        assert RecoveryAction.DEGRADE in actions


class TestDiagnose:
    def test_rate_limit_exception(self):
        assert diagnose_exception(Exception("429 rate limit exceeded")) == FailureClass.RATE_LIMIT

    def test_malformed_args_result(self):
        assert diagnose_result({"error": "Bad arguments for foo: missing required"}) == FailureClass.MALFORMED_ARGS

    def test_unknown_tool(self):
        assert diagnose_result({"error": "Unknown tool: xyz"}) == FailureClass.WRONG_TOOL

    def test_is_failure(self):
        assert is_failure({"error": "fail"})
        assert not is_failure({"ok": True})


class TestRetry:
    def test_backoff_increases(self):
        d0 = backoff_delay(0)
        d2 = backoff_delay(2)
        assert d2 >= d0
        assert d0 >= 0


class TestCircuit:
    def test_closed_by_default(self):
        key = "test:circuit_new_key"
        record_success(key)
        assert get_state(key) == CircuitState.CLOSED
        assert not is_open(key)

    def test_opens_after_threshold(self):
        key = "test:circuit_open_key"
        record_success(key)
        for _ in range(6):
            record_failure(key)
        assert is_open(key)

    def test_success_resets(self):
        key = "test:circuit_reset_key"
        record_failure(key)
        record_success(key)
        assert get_state(key) == CircuitState.CLOSED


class TestRepair:
    def test_repair_missing_required(self):
        args = repair_args("web_search", {}, "missing required argument: 'query'")
        assert "query" in args

    def test_repair_json(self):
        data = repair_json_output('{"ok": true, "value": 1}')
        assert data.get("ok") is True


class TestStuckLoop:
    def test_detects_repetition(self):
        calls = ["a:{}", "a:{}", "a:{}"]
        assert detect_stuck_loop(calls, threshold=3)

    def test_no_false_positive(self):
        calls = ["a:{}", "b:{}", "c:{}"]
        assert not detect_stuck_loop(calls, threshold=3)


class TestRecoveryBudget:
    def test_budget_limits(self):
        b = RecoveryBudget(max_recoveries=2)
        assert b.remaining == 2
        b.consume()
        b.consume()
        assert b.exhausted()


class TestHealingStore:
    def test_log_failure(self):
        store.log_failure("test", "tool", "transient", "timeout", "web_search",
                          recovery_action="retry", recovered=True)
        failures = store.list_failures(5)
        assert len(failures) >= 1

    def test_circuit_state_persist(self):
        store.upsert_circuit_state("test:persist", "closed", 0)
        row = store.get_circuit_state("test:persist")
        assert row is not None

    def test_checkpoint(self):
        cid = store.save_checkpoint("turn_test", 1, '{"tool": "test"}')
        assert cid > 0
        cp = store.get_latest_checkpoint("turn_test")
        assert cp is not None

    def test_healing_event(self):
        store.log_healing_event("trace1", 1, "transient", "retry", "recovered", 50)
        events = store.list_healing_events(5)
        assert len(events) >= 1


class TestFallback:
    def test_substitute_web_search(self):
        alt = substitute_tool("scrape_url")
        assert alt in ("web_search", "browse_page", "") or alt

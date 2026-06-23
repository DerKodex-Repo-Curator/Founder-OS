"""Unit tests for LECE (Lived-Experience Cognitive Engine)."""
import json
import os
import tempfile
import time

import pytest

from agent.cognition import episodes, sandbox, twin, principles, trust, metrics
from agent import store, trace


class TestEpisodes:
    def test_segment_trace(self):
        rec = {
            "id": "abc123",
            "message": "research investors",
            "final": "Found 3 investors",
            "events": [
                {"type": "tool", "data": {"name": "web_search", "decision": "allow",
                                           "result_preview": "success"}},
            ],
        }
        eps = episodes.segment_trace(rec)
        assert len(eps) >= 1
        assert eps[0]["trace_id"] == "abc123"

    def test_score_episode_success(self):
        ep = {"result_preview": "success completed", "decision": "allow", "final": "done"}
        assert episodes.score_episode(ep) >= 0.6

    def test_score_episode_failure(self):
        ep = {"result_preview": "error failed", "decision": "deny"}
        assert episodes.score_episode(ep) < 0.5


class TestSandbox:
    def test_simulation_intercepts_writes(self):
        assert not sandbox.is_simulation()
        with sandbox.SimulationContext():
            assert sandbox.is_simulation()
            assert sandbox.should_intercept("send_email")
        assert not sandbox.is_simulation()

    def test_simulate_tool_result(self):
        r = sandbox.simulate_tool_result("send_email", {"to": "a@b.com"}, {"predicted": "reply"})
        assert r.get("simulated") is True


class TestTwin:
    def test_state_key_stable(self):
        s = {"crm": {"by_status": {"lead": 2}}, "tasks_open": 1, "approvals_pending": 0, "goals": []}
        k1 = twin.state_key(s)
        k2 = twin.state_key(s)
        assert k1 == k2

    def test_action_key(self):
        k = twin.action_key("send_email", {"to": "x@y.com"})
        assert k.startswith("send_email:")

    def test_record_transition(self):
        twin.record_transition("test_tool", {"q": "1"}, "ok", True, 0.8)
        rows = store.list_twin_transitions(limit=5)
        assert any("test_tool" in r.get("action_key", "") for r in rows)


class TestPrinciples:
    def test_recall_empty(self):
        block = principles.recall_for_turn("nonexistent query xyz")
        assert isinstance(block, str)


class TestTrust:
    def test_record_and_get(self):
        trust.record_outcome("test_action_lece", True)
        trust.record_outcome("test_action_lece", True)
        score = store.get_trust_score("test_action_lece")
        assert score.get("trials", 0) >= 2

    def test_adaptive_decide_respects_floor(self):
        from agent.registry import get
        tool = get("send_email")
        if tool:
            d = trust.adaptive_decide(tool, {})
            assert d in ("allow", "approve", "deny")


class TestTraceIter:
    def test_iter_traces(self, tmp_path, monkeypatch):
        monkeypatch.setattr(trace, "TRACE_DIR", str(tmp_path))
        os.makedirs(tmp_path, exist_ok=True)
        path = os.path.join(tmp_path, time.strftime("%Y-%m-%d") + ".jsonl")
        rec = {"id": "t1", "ts": time.time(), "message": "hi", "final": "ok", "events": []}
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        rows = trace.iter_traces(limit=10)
        assert len(rows) >= 1
        assert rows[0]["id"] == "t1"


class TestMetrics:
    def test_full_report(self):
        r = metrics.full_report()
        assert "preplay" in r
        assert "principles" in r
        assert "trust" in r


class TestStoreLECE:
    def test_principle_crud(self):
        pid = store.add_principle("Always verify sources before CRM add", context="research")
        assert pid > 0
        rows = store.list_principles("active", 5)
        assert any(r["id"] == pid for r in rows)

    def test_workspace_post(self):
        wid = store.workspace_post("test", "hello workspace", salience=1.5)
        items = store.workspace_read(5)
        assert any(i["id"] == wid for i in items)

    def test_distill_run(self):
        rid = store.create_distill_run()
        store.finish_distill_run(rid, 10, 2, 1, detail="test")
        runs = store.list_distill_runs(3)
        assert runs[0]["id"] == rid

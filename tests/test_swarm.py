"""Unit tests for agent swarm orchestration."""
import pytest

from agent.swarm.topology import route_topology, topological_waves, Topology
from agent.swarm.handoff import HandoffSession, create_handoff_session
from agent import store


class TestTopology:
    def test_parallel_independent_steps(self):
        steps = [
            {"description": "a", "depends_on": []},
            {"description": "b", "depends_on": []},
            {"description": "c", "depends_on": []},
        ]
        assert route_topology("research 3 companies", steps) == Topology.PARALLEL

    def test_sequential_chain(self):
        steps = [
            {"description": "a", "depends_on": []},
            {"description": "b", "depends_on": [0]},
            {"description": "c", "depends_on": [1]},
        ]
        topo = route_topology("step by step plan", steps)
        assert topo in (Topology.SEQUENTIAL, Topology.HIERARCHICAL)

    def test_debate_hint(self):
        assert route_topology("debate whether to raise seed", hint="debate") == Topology.DEBATE

    def test_topological_waves(self):
        steps = [
            {"description": "a", "depends_on": []},
            {"description": "b", "depends_on": []},
            {"description": "c", "depends_on": [0, 1]},
        ]
        waves = topological_waves(steps)
        assert len(waves) == 2
        assert set(waves[0]) == {0, 1}
        assert waves[1] == [2]


class TestHandoff:
    def test_max_handoffs(self):
        import asyncio
        session = HandoffSession("test", "goal", max_handoffs=2)
        session.handoff_count = 2
        result = asyncio.run(session.handoff("ops"))
        assert "Max handoffs" in result.get("error", "")

    def test_loop_detection(self):
        import asyncio
        session = HandoffSession("test2", "goal", max_handoffs=10)
        session.chain = [("researcher", "t1"), ("ops", "t2"), ("researcher", "t3")]
        result = asyncio.run(session.handoff("researcher"))
        assert "loop" in result.get("error", "").lower()

    def test_create_session(self):
        session = create_handoff_session("test goal")
        assert session.session_id
        assert session.goal == "test goal"


class TestSwarmStore:
    def test_swarm_run_lifecycle(self):
        rid = store.create_swarm_run("test goal", "parallel", 3)
        assert rid > 0
        store.finish_swarm_run(rid, "done", "result text")
        runs = store.list_swarm_runs(5)
        assert any(r["id"] == rid for r in runs)

    def test_board_post_read(self):
        rid = store.create_swarm_run("board test", "blackboard", 1)
        eid = store.board_post(rid, "researcher", "finding", "test content", 1.5)
        assert eid > 0
        entries = store.board_read(rid)
        assert len(entries) >= 1

    def test_swarm_agent_pheromone(self):
        store.upsert_swarm_agent("test_agent", "worker", 1.0, "research tasks")
        store.update_swarm_agent_pheromone("test_agent", True, 0.1)
        profiles = store.list_swarm_agents("worker")
        assert any(p["name"] == "test_agent" for p in profiles)

    def test_job_queue(self):
        store.enqueue_swarm_job("test_job_1", "swarm", '{"goal": "test"}', 5)
        job = store.dequeue_swarm_job()
        if job.get("id") == "test_job_1":
            store.finish_swarm_job("test_job_1", "done", "ok")

"""Agent swarm orchestration package.

Implements all 12 swarm paths: orchestrator-worker, dynamic handoff, fan-out/fan-in,
adaptive topology, stigmergy/blackboard, bio-inspired profiles, debate, mesh,
hierarchical hybrid, MCP external, proactive heartbeat, self-evolving, framework
adapter, and distributed workers.
"""
from agent.swarm.runner import run_swarm, aggregate_results
from agent.swarm.topology import route_topology, Topology
from agent.swarm.handoff import HandoffSession, create_handoff_session
from agent.swarm.debate import run_debate, run_maker_checker
from agent.swarm.mesh import run_mesh
from agent.swarm.board import SwarmBoard, run_blackboard_round
from agent.swarm.profiles import assign_agent, reinforce_profile, list_profiles
from agent.swarm.hierarchy import run_hierarchical
from agent.swarm.proactive import run_proactive_swarm
from agent.swarm.evolve import run_evolve_swarm

__all__ = [
    "run_swarm", "aggregate_results", "route_topology", "Topology",
    "HandoffSession", "create_handoff_session", "run_debate", "run_maker_checker",
    "run_mesh", "SwarmBoard", "run_blackboard_round", "assign_agent",
    "reinforce_profile", "list_profiles", "run_hierarchical",
    "run_proactive_swarm", "run_evolve_swarm",
]

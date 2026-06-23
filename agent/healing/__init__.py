"""Self-healing control plane for Founder OS.

Monitor -> detect -> diagnose -> recover -> verify loop with bounded recovery budget.
"""
from agent.healing.orchestrator import heal_call, RecoveryBudget, healing_enabled
from agent.healing.taxonomy import FailureClass, RecoveryAction

__all__ = [
    "heal_call", "RecoveryBudget", "healing_enabled",
    "FailureClass", "RecoveryAction",
]

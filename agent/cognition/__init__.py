"""Lived-Experience Cognitive Engine (LECE).

Continual self-distillation from traces, business digital twin + preplay,
and Global Workspace attention coordination.
"""
from agent.cognition.distill import run_distillation
from agent.cognition.principles import recall_for_step, recall_for_turn
from agent.cognition.manual import build_manual_prefix
from agent.cognition.twin import build_state_vector, snapshot_for_preplay
from agent.cognition.preplay import maybe_preplay, record_actual_outcome
from agent.cognition.workspace import broadcast_block, post_item, tick_decay
from agent.cognition.trust import adaptive_decide, record_outcome
from agent.cognition.loop import start_cognitive_loop, stop_cognitive_loop

__all__ = [
    "run_distillation",
    "recall_for_step",
    "recall_for_turn",
    "build_manual_prefix",
    "build_state_vector",
    "snapshot_for_preplay",
    "maybe_preplay",
    "record_actual_outcome",
    "broadcast_block",
    "post_item",
    "tick_decay",
    "adaptive_decide",
    "record_outcome",
    "start_cognitive_loop",
    "stop_cognitive_loop",
]

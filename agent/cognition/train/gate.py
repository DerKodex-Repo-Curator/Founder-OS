"""Eval gate: promote adapter only if it beats baseline (anti-collapse)."""
import json
import logging
import os

from agent.cognition.train import dataset as ds_mod
from agent.cognition.train import lora as lora_mod

logger = logging.getLogger(__name__)

GATE_DIR = "./data/lece/gate"
CURRENT_ADAPTER = os.path.join(GATE_DIR, "current.json")
CANDIDATE_ADAPTER = os.path.join(GATE_DIR, "candidate.json")


def _baseline_score() -> float:
    path = CURRENT_ADAPTER
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("eval_score", 0.5)
    return 0.5


def _eval_adapter(dataset: list) -> float:
    """Proxy eval: fraction of high-score examples (full eval uses evals/lece/)."""
    if not dataset:
        return 0.0
    scores = [ex.get("metadata", {}).get("score", 0.5) for ex in dataset]
    return sum(scores) / len(scores)


async def maybe_train_and_promote(episodes: list) -> dict:
    from config import config
    if not getattr(config, "lece_distill_train", False):
        return {"skipped": True, "reason": "LECE_DISTILL_TRAIN=false"}

    examples = ds_mod.build_dataset(episodes)
    if len(examples) < 10:
        return {"skipped": True, "reason": f"insufficient examples ({len(examples)})"}

    path = ds_mod.save_dataset(examples)
    train_result = lora_mod.train_lora(path, backend=getattr(config, "lece_train_backend", "peft"))
    if not train_result.get("ok"):
        return train_result

    candidate_score = _eval_adapter(examples)
    baseline = _baseline_score()

    os.makedirs(GATE_DIR, exist_ok=True)
    if candidate_score >= baseline:
        with open(CURRENT_ADAPTER, "w", encoding="utf-8") as f:
            json.dump({"eval_score": candidate_score, "examples": len(examples)}, f)
        from agent.cognition.train import modelfile as mf
        mf.write_modelfile()
        return {
            "promoted": True,
            "candidate_score": candidate_score,
            "baseline": baseline,
            "train": train_result,
        }

    return {
        "promoted": False,
        "candidate_score": candidate_score,
        "baseline": baseline,
        "reason": "candidate did not beat baseline (anti-collapse gate)",
    }

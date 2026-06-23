"""Build SFT dataset from successful trajectories for local LoRA training."""
import json
import os

DATASET_DIR = "./data/lece/training"


def build_dataset(episodes: list, min_score: float = 0.65) -> list:
    """Convert off-policy episodes to chat-format training examples."""
    examples = []
    for ep in episodes:
        if ep.get("score", 0) < min_score:
            continue
        msg = ep.get("message", "")
        final = ep.get("final", ep.get("result_preview", ""))
        if not msg or not final:
            continue
        examples.append({
            "messages": [
                {"role": "user", "content": msg[:1500]},
                {"role": "assistant", "content": final[:1500]},
            ],
            "metadata": {
                "trace_id": ep.get("trace_id", ""),
                "tools": ep.get("tools", []),
                "score": ep.get("score", 0),
            },
        })
    return examples


def save_dataset(examples: list, name: str = "lece_sft") -> str:
    os.makedirs(DATASET_DIR, exist_ok=True)
    path = os.path.join(DATASET_DIR, f"{name}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, default=str) + "\n")
    return path


def load_dataset(path: str = None) -> list:
    path = path or os.path.join(DATASET_DIR, "lece_sft.jsonl")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

"""LoRA trainer scaffold — lazy import, no-op without GPU/peft."""
import logging
import os

logger = logging.getLogger(__name__)

ADAPTER_DIR = "./data/lece/adapters"


def train_lora(dataset_path: str, backend: str = "peft") -> dict:
    """Attempt LoRA fine-tune. Returns status dict."""
    if not os.path.exists(dataset_path):
        return {"ok": False, "error": "dataset not found", "path": dataset_path}

    try:
        if backend == "unsloth":
            return _train_unsloth(dataset_path)
        return _train_peft(dataset_path)
    except ImportError as e:
        return {
            "ok": False,
            "skipped": True,
            "error": f"Training backend unavailable: {e}. "
                     "Install peft+transformers+torch or set LECE_DISTILL_TRAIN=false.",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


def _train_peft(dataset_path: str) -> dict:
    """Scaffold: validates deps and writes placeholder adapter manifest."""
    import peft  # noqa: F401
    import transformers  # noqa: F401

    os.makedirs(ADAPTER_DIR, exist_ok=True)
    manifest = os.path.join(ADAPTER_DIR, "latest_manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        import json
        json.dump({
            "status": "scaffold_ready",
            "dataset": dataset_path,
            "note": "Full training loop requires GPU. Run scripts/train_lece_lora.py manually.",
        }, f, indent=2)
    return {
        "ok": True,
        "scaffold": True,
        "manifest": manifest,
        "message": "Training scaffold validated. Full LoRA run requires GPU + manual script.",
    }


def _train_unsloth(dataset_path: str) -> dict:
    import unsloth  # noqa: F401
    return _train_peft(dataset_path)

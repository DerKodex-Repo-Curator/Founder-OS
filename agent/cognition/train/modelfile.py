"""Ollama Modelfile generator for promoted LECE adapters."""
import os

from config import config

MODELFILE_PATH = "./data/lece/Modelfile"


def write_modelfile(base_model: str = None, adapter_path: str = None) -> str:
    base = base_model or config.ollama_model
    adapter = adapter_path or "./data/lece/adapters/latest"
    os.makedirs(os.path.dirname(MODELFILE_PATH), exist_ok=True)
    content = f"""# LECE personalized adapter (generated)
FROM {base}

# Adapter weights (when trained):
# ADAPTER {adapter}

SYSTEM \"\"\"You are a personalized Founder OS instance distilled from this founder's lived experience.\"\"\"

PARAMETER temperature 0.7
"""
    with open(MODELFILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    return MODELFILE_PATH


def load_instructions() -> str:
    if not os.path.exists(MODELFILE_PATH):
        return "Modelfile not generated yet. Enable LECE_DISTILL_TRAIN and run distillation."
    with open(MODELFILE_PATH, "r", encoding="utf-8") as f:
        return f.read()

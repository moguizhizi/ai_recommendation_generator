# configs/loader.py
import yaml
from pathlib import Path

def load_config(path: str = None):
    if path is None:
        path = Path(__file__).parent / "config.yaml"

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
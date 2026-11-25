"""Common helpers: seeding, device selection, config loading, logging."""
import os
import random
import copy
import numpy as np
import torch
import yaml


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device(pref: str = "auto") -> str:
    if pref == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return pref


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def deep_update(base: dict, override: dict) -> dict:
    """Return a copy of `base` with keys from `override` merged in recursively."""
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = v
    return out


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def log(msg: str) -> None:
    print(msg, flush=True)

"""Carga de configuración experimental + hash (benchmark_y_persistencia.md)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_hash(cfg: dict) -> str:
    canonical = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

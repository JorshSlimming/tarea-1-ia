"""Derivación determinista de seeds (docs/02_decisiones/fuego.md).

Usa hashlib, nunca hash() de Python (depende de PYTHONHASHSEED).
"""

from __future__ import annotations

import hashlib
import random


def derive_seed(base_seed: int, *parts: object) -> int:
    msg = f"{base_seed}:" + ":".join(str(p) for p in parts)
    digest = hashlib.sha256(msg.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def make_rng(base_seed: int, *parts: object) -> random.Random:
    return random.Random(derive_seed(base_seed, *parts))

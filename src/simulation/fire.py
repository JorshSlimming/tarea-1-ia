"""Propagación de fuego (docs/02_decisiones/fuego.md, testing.md).

- Ortogonal, irreversible, muros y salida no arden.
- Las celdas nuevas no propagan en el mismo evento.
- Timeline[t] = fuego activo al inicio del turno t (longitud max_turns+1).
- Evento tras el turno t si (t+1) % k == 0.
"""

from __future__ import annotations

import random

from src.domain.models import StaticMap
from src.domain.enums import Terrain

NEIGHBORS: tuple[tuple[int, int], ...] = ((-1, 0), (0, 1), (1, 0), (0, -1))


def is_flammable(smap: StaticMap, row: int, col: int) -> bool:
    if not smap.in_bounds(row, col):
        return False
    t = smap.grid[row][col]
    return t is not Terrain.WALL and t is not Terrain.EXIT


def precompute_timeline(
    smap: StaticMap,
    origin: tuple[int, int],
    k: int,
    p: float,
    max_turns: int,
    fire_rng: random.Random,
) -> tuple[frozenset, ...]:
    if k < 1:
        raise ValueError(f"k debe ser >= 1, got {k}")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p debe estar en [0,1], got {p}")
    burning: set[tuple[int, int]] = {origin}
    timeline: list[frozenset] = [frozenset(burning)]
    for t in range(max_turns):
        if (t + 1) % k == 0:
            current = sorted(burning)
            new: set[tuple[int, int]] = set()
            for r, c in current:
                for dr, dc in NEIGHBORS:
                    nxt = (r + dr, c + dc)
                    if nxt in burning or nxt in new:
                        continue
                    if not is_flammable(smap, nxt[0], nxt[1]):
                        continue
                    if fire_rng.random() < p:
                        new.add(nxt)
            burning |= new
        timeline.append(frozenset(burning))
    return tuple(timeline)

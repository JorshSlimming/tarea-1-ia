"""Resolución de conflictos de movimiento simultáneo.

Regla (docs/02_decisiones/congestion_y_movimiento.md):
    ocupacion_final(d) = stayers(d) + concedidos(d) <= capacidad(d)

Algoritmo: punto fijo. Se conceden entradas por destino según stayers
actuales; los rechazados pasan a stayers; si un stayer nuevo llena una
celda con concesiones previas, se revocan las de menor prioridad y los
revocados también quedan quietos. Termina porque stayers solo crece y
concesiones solo decrecen (cota: nº agentes).

- Swaps A<->B y cadenas se permiten: salen del modelo sin caso especial.
- Desempate determinista: derive_seed(conflict_seed, turno, destino, id).
- WAIT elegido -> voluntary; movimiento rechazado o inválido -> congestion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.enums import Action
from .rng import derive_seed
from .state import Snapshot, apply_action


@dataclass
class ConflictOutcome:
    dest: dict[int, tuple[int, int]]
    voluntary_wait: set[int] = field(default_factory=set)
    congestion_wait: set[int] = field(default_factory=set)
    invalid_intent: set[int] = field(default_factory=set)


def _priority(
    conflict_seed: int, turn: int, dest: tuple[int, int], aid: int
) -> tuple[int, int]:
    return (derive_seed(conflict_seed, turn, dest[0], dest[1], aid), aid)


def resolve(
    snapshot: Snapshot,
    intentions: dict[int, Action],
    positions: dict[int, tuple[int, int]],
    conflict_seed: int,
    turn: int,
) -> ConflictOutcome:
    aids = sorted(positions)
    desired: dict[int, tuple[int, int]] = {}
    invalid: set[int] = set()
    for aid in aids:
        action = intentions.get(aid, Action.WAIT)
        d = apply_action(snapshot, positions[aid], action)
        if d is None:  # muro/fuego/fuera: queda quieto
            invalid.add(aid)
            desired[aid] = positions[aid]
        else:
            desired[aid] = d

    voluntary = {a for a in aids if intentions.get(a, Action.WAIT) is Action.WAIT}
    stayers0 = {a for a in aids if desired[a] == positions[a]}
    movers = [a for a in aids if desired[a] != positions[a]]

    rejected: set[int] = set()
    granted: dict[int, tuple[int, int]] = {}
    while True:
        stay_count: dict[tuple[int, int], int] = {}
        for a in stayers0 | rejected:
            c = positions[a]
            stay_count[c] = stay_count.get(c, 0) + 1
        by_dest: dict[tuple[int, int], list[int]] = {}
        for a in movers:
            if a not in rejected:
                by_dest.setdefault(desired[a], []).append(a)
        granted = {}
        new_rejected: set[int] = set()
        for dest, cands in by_dest.items():
            slots = snapshot.capacity_at(*dest) - stay_count.get(dest, 0)
            ordered = sorted(
                cands, key=lambda a: _priority(conflict_seed, turn, dest, a)
            )
            keep = ordered[: max(slots, 0)]
            for a in keep:
                granted[a] = dest
            for a in ordered[max(slots, 0) :]:
                new_rejected.add(a)
        new_rejected -= rejected
        if not new_rejected:
            break
        rejected |= new_rejected

    dest = {a: granted.get(a, positions[a]) for a in aids}
    congested = {
        a
        for a in aids
        if a not in voluntary and dest[a] == positions[a] and desired[a] != positions[a]
    }
    return ConflictOutcome(
        dest=dest,
        voluntary_wait={a for a in voluntary if dest[a] == positions[a]},
        congestion_wait=congested,
        invalid_intent=invalid,
    )

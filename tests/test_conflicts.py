"""Tests F4: conflictos (testing.md: 3 agentes/1 cupo, desempate, swap, cadena).

Mapa local 5x5 con celda estrecha 'n' en (2,2) y salida en (4,2).
Nota: el engine garantiza ocupacion inicial <= capacidad (spawn la respeta
y el resolver la preserva); los tests aleatorios muestrean dentro de ese
invariante en vez de apilar agentes arbitrariamente.
"""

import random
from collections import Counter

import pytest

from src.domain.enums import Action
from src.domain.map import parse_map
from src.simulation.conflicts import resolve
from src.simulation.state import SimulationState, make_snapshot

ROWS = [
    "#####",
    "#...#",
    "#.n.#",
    "#...#",
    "##E##",
]


@pytest.fixture()
def snap():
    sm = parse_map(ROWS, "room5")
    return make_snapshot(SimulationState(smap=sm))


def test_three_agents_one_narrow_slot_grants_exactly_one(snap):
    # (2,2) es 'n' C=1: tres solicitantes, solo uno entra.
    pos = {0: (2, 1), 1: (2, 3), 2: (1, 2)}
    inten = {0: Action.RIGHT, 1: Action.LEFT, 2: Action.DOWN}
    out = resolve(snap, inten, pos, 1234, 0)
    arrivals = [a for a, d in out.dest.items() if d == (2, 2)]
    assert len(arrivals) == 1
    for a in pos:
        if a not in arrivals:
            assert a in out.congestion_wait


def test_floor_two_slots_grants_two(snap):
    # (3,2) es piso C=2: tres solicitantes, entran dos.
    pos = {0: (3, 1), 1: (3, 3), 2: (2, 2)}
    inten = {0: Action.RIGHT, 1: Action.LEFT, 2: Action.DOWN}
    out = resolve(snap, inten, pos, 999, 7)
    arrivals = [a for a, d in out.dest.items() if d == (3, 2)]
    assert len(arrivals) == 2
    for a in pos:
        if a not in arrivals:
            assert a in out.congestion_wait


def test_deterministic_tiebreak(snap):
    pos = {0: (3, 1), 1: (3, 3)}
    inten = {0: Action.RIGHT, 1: Action.LEFT}  # ambos a (3,2) C=2: caben
    o1 = resolve(snap, inten, pos, 555, 3)
    o2 = resolve(snap, inten, pos, 555, 3)
    assert o1.dest == o2.dest
    assert o1.dest[0] == (3, 2) and o1.dest[1] == (3, 2)


def test_swap_allowed(snap):
    # A<->B simultáneo: ocupación final igual, se permite.
    out = resolve(
        snap, {0: Action.RIGHT, 1: Action.LEFT}, {0: (2, 1), 1: (2, 2)}, 1, 0
    )
    assert out.dest[0] == (2, 2)
    assert out.dest[1] == (2, 1)


def test_chain_allowed(snap):
    out = resolve(
        snap,
        {0: Action.RIGHT, 1: Action.RIGHT, 2: Action.RIGHT},
        {0: (3, 1), 1: (3, 2), 2: (3, 3)},
        1, 0,
    )
    # (3,1)->(3,2)->(3,3)->(3,4): cadena válida, capacidades piso C=2.
    assert out.dest[0] == (3, 2)
    assert out.dest[1] == (3, 3)


def _slots(snap):
    """Lista de (celda, k) con un slot por unidad de capacidad."""
    cells = [
        (r, c)
        for r in range(1, 4)
        for c in range(1, 4)
        if snap.is_traversable(r, c)
    ]
    return [(cell, k) for cell in cells for k in range(snap.capacity_at(*cell))]


def test_final_occupancy_within_capacity(snap):
    rng = random.Random(0)
    slots = _slots(snap)
    for _ in range(50):
        picks = rng.sample(slots, 6)
        pos = {i: cell for i, (cell, _) in enumerate(picks)}
        inten = {i: rng.choice(list(Action)) for i in range(6)}
        out = resolve(snap, inten, pos, 42, 1)
        counts = Counter(out.dest.values())
        for cell, n in counts.items():
            assert n <= snap.capacity_at(*cell), (cell, n)


def test_voluntary_vs_congestion_wait(snap):
    out = resolve(
        snap, {0: Action.WAIT, 1: Action.RIGHT},
        {0: (3, 2), 1: (3, 1)}, 7, 0,
    )
    assert 0 in out.voluntary_wait
    # 1 quiere (3,2) con 0 quieto: 1+1 <= 2 cabe.
    assert out.dest[1] == (3, 2)

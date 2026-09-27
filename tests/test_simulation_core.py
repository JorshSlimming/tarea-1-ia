"""Tests F2/F3: congestión, snapshot, RNG, fuego, scenario (testing.md)."""

import pytest

from src.domain.enums import Action, AgentStatus
from src.domain.map import load_map, manhattan
from src.simulation.fire import precompute_timeline
from src.simulation.rng import derive_seed, make_rng
from src.simulation.scenario import build_scenario
from src.simulation.state import (
    SimulationState,
    apply_action,
    make_snapshot,
    rebuild_occupancy,
    transition_cost,
)
from src.domain.models import Agent

MAPS = ["map1", "map2", "map3"]


def test_congestion_cost_reference_values():
    # testing.md: C2/o0 -> 1, C2/o1 -> 2, C2/o2 -> 5 (lam=4).
    assert transition_cost(0, 2) == 1.0
    assert transition_cost(1, 2) == 2.0
    assert transition_cost(2, 2) == 5.0
    assert transition_cost(1, 1) == 5.0


def test_snapshot_traversable_excludes_fire():
    sm = load_map("maps/map2.txt")
    fire = frozenset({(5, 5)})
    st = SimulationState(smap=sm, fire_cells=fire)
    snap = make_snapshot(st)
    assert not snap.is_traversable(*next(iter(fire)))
    assert snap.is_traversable(*sm.exit_pos)


def test_occupancy_counts_active_only():
    sm = load_map("maps/map3.txt")
    st = SimulationState(
        smap=sm,
        agents=[
            Agent(0, (5, 5)),
            Agent(1, (5, 5)),
            Agent(2, (5, 5), status=AgentStatus.DEAD),
            Agent(3, (6, 6), status=AgentStatus.EVACUATED),
        ],
    )
    rebuild_occupancy(st)
    assert st.occupancy == {(5, 5): 2}


def test_apply_action_blocked_by_wall():
    sm = load_map("maps/map2.txt")
    st = SimulationState(smap=sm)
    snap = make_snapshot(st)
    # (0,0) es muro: cualquier vecino fuera o muro -> None salvo WAIT.
    assert apply_action(snap, (0, 0), Action.UP) is None
    assert apply_action(snap, (5, 5), Action.WAIT) == (5, 5)


def test_heuristic_never_overestimates_open():
    sm = load_map("maps/map3.txt")
    st = SimulationState(smap=sm)
    snap = make_snapshot(st)
    # En mapa abierto el costo real >= Manhattan (costo minimo 1 por paso).
    assert snap.heuristic_to_exit(12, 12) == manhattan((12, 12), sm.exit_pos)


def test_rng_deterministic_and_hashlib_based():
    assert derive_seed(7, "x") == derive_seed(7, "x")
    assert derive_seed(7, "x") != derive_seed(8, "x")
    assert derive_seed(7, "x") != derive_seed(7, "y")
    r1 = make_rng(42, "fire", "map1")
    r2 = make_rng(42, "fire", "map1")
    assert [r1.random() for _ in range(5)] == [r2.random() for _ in range(5)]


def test_fire_timeline_reproducible_and_rules():
    sm = load_map("maps/map3.txt")
    origin = next(
        (r, c)
        for r in range(sm.rows)
        for c in range(sm.cols)
        if sm.grid[r][c].name == "FLOOR" and manhattan((r, c), sm.exit_pos) > 10
    )
    t1 = precompute_timeline(sm, origin, 3, 0.3, 30, make_rng(1, "fire"))
    t2 = precompute_timeline(sm, origin, 3, 0.3, 30, make_rng(1, "fire"))
    assert t1 == t2
    assert len(t1) == 31
    # Irreversible + muros/salida nunca arden.
    for i in range(1, len(t1)):
        assert t1[i - 1] <= t1[i]
    for cells in t1:
        for r, c in cells:
            assert sm.grid[r][c].name in ("FLOOR", "NARROW")


def test_fire_no_same_event_propagation():
    # p=1 en corredor: cada evento avanza exactamente 1 celda (sin cascada).
    from src.domain.map import parse_map

    rows = ["#####", "#...E", "#####"]
    sm = parse_map(rows, "corridor")
    tl = precompute_timeline(sm, (1, 1), k=1, p=1.0, max_turns=3,
                             fire_rng=make_rng(0, "t"))
    assert tl[1] == frozenset({(1, 1), (1, 2)})
    assert tl[2] == frozenset({(1, 1), (1, 2), (1, 3)})


@pytest.mark.parametrize("map_id", MAPS)
def test_scenario_reproducible_and_valid(map_id):
    s1 = build_scenario(load_map(f"maps/{map_id}.txt"), 10000)
    s2 = build_scenario(load_map(f"maps/{map_id}.txt"), 10000)
    assert s1 == s2
    assert len(s1.spawns) == 30
    assert len(set(s1.spawns)) == 30
    assert all(manhattan(s, s1.fire_origin) >= 4 for s in s1.spawns)
    assert manhattan(s1.fire_origin, load_map(f"maps/{map_id}.txt").exit_pos) >= 6
    assert len(s1.fire_timeline) == 201  # max_turns+1

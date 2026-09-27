"""Tests F6-F9: búsquedas clásicas (testing.md).

- BFS: mínimo número de pasos.
- UCS: evita costo alto (congestion).
- Greedy: prioriza Manhattan.
- A*: óptimo en casos pequeños (== UCS en costo).
- Manhattan: no sobreestima (admisible en casos diseñados).
"""

import pytest

from src.domain.enums import Action
from src.domain.map import parse_map
from src.planners.astar import AStarPlanner
from src.planners.bfs import BFSPlanner
from src.planners.greedy import GreedyPlanner
from src.planners.uniform_cost import UCSPlanner
from src.simulation.state import SimulationState, make_snapshot
from src.domain.models import Agent

OPEN = ["#######", "#.....#", "#.....#", "#.....#", "#..E..#", "#######"]


def _snap(rows, occupancy=None):
    sm = parse_map(rows, "t")
    agents = []
    if occupancy:
        aid = 0
        for pos, n in occupancy.items():
            for _ in range(n):
                agents.append(Agent(id=aid, position=pos))
                aid += 1
    st = SimulationState(smap=sm, agents=agents)
    from src.simulation.state import rebuild_occupancy

    rebuild_occupancy(st)
    return make_snapshot(st), sm


def test_bfs_min_steps_open():
    snap, sm = _snap(OPEN)
    start = (1, 1)
    r = BFSPlanner().plan(snap, start, sm.exit_pos)
    assert r.success
    assert r.path[0] == start and r.path[-1] == sm.exit_pos
    # En este mapa abierto, el mínimo coincide con Manhattan: 5 pasos.
    assert len(r.actions) == 5
def test_ucs_avoids_congested_cell():
    # Fila con celda central ocupada (C=2,o=2 -> costo 5) vs rodeo por arriba.
    rows = ["########", "#......#", "#......#", "#..E...#", "########"]
    occ = {(2, 3): 2}  # paso directo encarecido
    snap, sm = _snap(rows, occupancy=occ)
    ucs = UCSPlanner().plan(snap, (2, 1), sm.exit_pos)
    bfs = BFSPlanner().plan(snap, (2, 1), sm.exit_pos)
    assert ucs.success and bfs.success
    assert ucs.path_cost <= bfs.path_cost + 1e-9


def test_ucs_cheaper_than_bfs_under_congestion():
    # Corredor con dos rutas: directa corta por celda llena (costo 5+1)
    # vs rodeo largo pero barato. UCS debe preferir menor costo total.
    rows = ["#########", "#...#...#", "#...#...#", "#...E...#", "#########"]
    occ = {(2, 3): 2, (1, 3): 2}  # columna central llena
    snap, sm = _snap(rows, occupancy=occ)
    ucs = UCSPlanner().plan(snap, (1, 1), sm.exit_pos)
    bfs = BFSPlanner().plan(snap, (1, 1), sm.exit_pos)
    assert ucs.success and bfs.success
    assert ucs.path_cost <= bfs.path_cost + 1e-9
    assert len(ucs.actions) >= len(bfs.actions)  # rodeo: mas pasos, menos costo



def test_greedy_prioritizes_manhattan():
    snap, sm = _snap(OPEN)
    r = GreedyPlanner().plan(snap, (1, 1), sm.exit_pos)
    assert r.success
    assert r.path[-1] == sm.exit_pos
    # Primera acción reduce Manhattan (h greedy).
    from src.domain.map import manhattan

    nxt = (1 + r.actions[0].delta[0], 1 + r.actions[0].delta[1])
    assert manhattan(nxt, sm.exit_pos) < manhattan((1, 1), sm.exit_pos)


def test_astar_optimal_small_case_equals_ucs():
    rows = ["######", "#....#", "#.E..#", "#....#", "######"]
    occ = {(2, 2): 1}
    snap, sm = _snap(rows, occupancy=occ)
    a = AStarPlanner().plan(snap, (1, 1), sm.exit_pos)
    u = UCSPlanner().plan(snap, (1, 1), sm.exit_pos)
    assert a.success and u.success
    assert abs(a.path_cost - u.path_cost) < 1e-9


def test_manhattan_admissible_designed_cases():
    snap, sm = _snap(OPEN)
    cases = [(1, 1), (1, 5), (3, 1), (3, 5)]
    for pos in cases:
        h = snap.heuristic_to_exit(*pos)
        r = AStarPlanner().plan(snap, pos, sm.exit_pos)
        assert r.success
        assert h <= r.path_cost + 1e-9


def test_failure_when_walled_off():
    rows = ["#####", "#.#E#", "#.#.#", "#.#.#", "#####"]
    snap, sm = _snap(rows)
    # Columna de muros parte el mapa; (1,1) queda sin ruta a la salida.
    for planner in (BFSPlanner(), UCSPlanner(), GreedyPlanner(), AStarPlanner()):
        r = planner.plan(snap, (1, 1), sm.exit_pos)
        assert not r.success
        assert r.actions == ()


def test_fire_cells_are_not_successors():
    snap, sm = _snap(OPEN)
    fire_snap = make_snapshot(
        SimulationState(smap=sm, fire_cells=frozenset({sm.exit_pos}))
    )
    # Salida en llamas nunca ocurre (no arde), pero una celda de fuego
    # intermedia sí debe bloquearse: quemar el paso obliga a rodear/fallar.
    from src.simulation.state import Snapshot

    blocked = Snapshot(
        turn=0, smap=sm, fire_cells=frozenset({(3, 3), (2, 3)}),
        occupancy=(), lam=4.0,
    )
    r = BFSPlanner().plan(blocked, (1, 3), sm.exit_pos)
    # Sin pasar por fuego: o rodea o falla, pero nunca pisa fuego.
    if r.success:
        assert not ({(3, 3), (2, 3)} & set(r.path))

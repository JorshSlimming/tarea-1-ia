"""Tests F5: engine sin IA compleja (stub planner) + trapped (testing.md).

Stub: planner determinista que propone un paso fijo o WAIT; el engine
resuelve terminación, muertes y trapped sin depender de BFS/A*.
"""

import pytest

from src.domain.enums import Action, AgentStatus
from src.domain.map import load_map, parse_map
from src.domain.models import PlanResult, Scenario
from src.simulation.engine import SimulationEngine
from src.simulation.scenario import build_scenario
from src.simulation.state import Snapshot
from src.planners.base import Planner


class StepPlanner(Planner):
    """Propone siempre la misma acción (si success) o failure."""

    name = "stub"

    def __init__(self, action=Action.WAIT, success=True):
        self.action = action
        self.success = success

    def plan(self, snapshot, start, goal, *, agent_id=0, turn=0):
        return PlanResult(success=self.success, actions=(self.action,))


class GreedyEast(Planner):
    """Camina hacia el este si puede, si no WAIT (para test de evacuación)."""

    name = "stub-east"

    def plan(self, snapshot: Snapshot, start, goal, *, agent_id=0, turn=0):
        if start == goal:
            return PlanResult(success=True, actions=(Action.WAIT,))
        dr = goal[0] - start[0]
        dc = goal[1] - start[1]
        for a in (Action.UP, Action.RIGHT, Action.DOWN, Action.LEFT):
            ddr, ddc = a.delta
            nxt = (start[0] + ddr, start[1] + ddc)
            if snapshot.is_traversable(*nxt):
                # Preferir el que más acerca a la salida.
                pass
        # Simple: elige vecino que minimiza Manhattan.
        best, best_d = Action.WAIT, abs(dr) + abs(dc)
        for a in (Action.UP, Action.RIGHT, Action.DOWN, Action.LEFT):
            ddr, ddc = a.delta
            nxt = (start[0] + ddr, start[1] + ddc)
            if snapshot.is_traversable(*nxt):
                d = abs(goal[0] - nxt[0]) + abs(goal[1] - nxt[1])
                if d < best_d:
                    best, best_d = a, d
        return PlanResult(success=True, actions=(best,))


def _scenario_no_fire(map_id="map3", seed=10000, max_turns=200):
    sm = load_map(f"maps/{map_id}.txt")
    sc = build_scenario(sm, seed, max_turns=max_turns)
    # Timeline sin fuego: engine usa el provisto si se pasa explícito.
    empty = tuple([frozenset()] * (max_turns + 1))
    return sc, empty


def test_all_wait_timeout_marks_trapped():
    sc, empty = _scenario_no_fire(max_turns=5)
    eng = SimulationEngine(sc, StepPlanner(Action.WAIT), max_turns=5,
                           fire_timeline=empty)
    m = eng.run()
    assert m.evacuated == 0 and m.dead == 0
    assert m.trapped == 30
    assert m.finished_reason == "TIMEOUT"
    assert m.clearance_turn is None  # sin evacuados -> NaN/null
    assert m.turns == 5


def test_failure_is_not_trapped_immediately():
    sc, empty = _scenario_no_fire(max_turns=3)
    eng = SimulationEngine(sc, StepPlanner(success=False), max_turns=3,
                           fire_timeline=empty)
    m = eng.run()
    # failure -> WAIT voluntario, al timeout TRAPPED(TIMEOUT), nunca antes.
    assert all(a["status"] == "TRAPPED" for a in m.per_agent)
    assert all(a["status_reason"] == "TIMEOUT" for a in m.per_agent)
    assert sum(a["voluntary_waits"] for a in m.per_agent) == 30 * 3


def test_evacuation_terminates_all_resolved():
    # Planner directo: BFS real sobre snapshot sin fuego. En map3 abierto
    # todos deben evacuar (unico limite: capacidad 1/turno de la salida).
    from src.planners.bfs import BFSPlanner


    sc, empty = _scenario_no_fire(map_id="map3", max_turns=200)
    eng = SimulationEngine(sc, BFSPlanner(), max_turns=200, fire_timeline=empty)
    m = eng.run()
    assert m.finished_reason == "ALL_RESOLVED"
    assert m.evacuated + m.dead + m.trapped == 30
    assert m.evacuated == 30
    assert m.clearance_turn is not None and m.clearance_turn >= 1
    assert m.clearance_turn == max(
        a["evacuation_turn"] for a in m.per_agent if a["status"] == "EVACUATED"
    )




def test_fire_kills_agent_on_cell():
    from src.domain.map import parse_map

    rows = ["#####", "#...#", "#.E.#", "#...#", "#####"]
    sm = parse_map(rows, "firetest")
    sc = Scenario(map_id="firetest", seed=1, spawns=((1, 1),),
                  fire_origin=(1, 1),
                  fire_timeline=(frozenset({(1, 1)}), frozenset({(1, 1)})),
                  conflict_seed=1, ga_seed=1)
    eng = SimulationEngine.__new__(SimulationEngine)
    # Inyectar mapa pequeño sin pasar por maps/.
    from src.experiment.metrics import RunMetrics
    from src.simulation.state import SimulationState, rebuild_occupancy
    from src.domain.models import Agent

    eng.scenario, eng.planner, eng.max_turns, eng.lam = sc, StepPlanner(), 5, 4.0
    eng.smap, eng.timeline = sm, sc.fire_timeline
    eng.metrics = RunMetrics(algorithm="stub", map_id="firetest", seed=1)
    eng.is_ga = False
    eng.state = SimulationState(smap=sm, agents=[Agent(id=0, position=(1, 1))])
    rebuild_occupancy(eng.state)
    m = eng.run()
    assert m.dead == 1
    assert m.per_agent[0]["death_turn"] == 0
    assert eng.state.occupancy == {}


def test_trapped_by_fire_cut_corridor():
    # Corredor 1x5: fuego corta el paso -> el agente queda TRAPPED(DISCONNECTED).
    from src.domain.map import parse_map

    sm2 = parse_map(["#######", "#....E#", "#######"], "corr")
    tl = (
        frozenset(),                       # t0: sin fuego
        frozenset({(1, 3)}),                # t1: fuego corta corredor
        frozenset({(1, 3)}),
        frozenset({(1, 3)}),
    )
    sc = Scenario(map_id="corr", seed=2, spawns=((1, 1),), fire_origin=(1, 3),
                  fire_timeline=tl, conflict_seed=2, ga_seed=2)
    eng = SimulationEngine.__new__(SimulationEngine)
    from src.experiment.metrics import RunMetrics
    from src.simulation.state import SimulationState, rebuild_occupancy
    from src.domain.models import Agent

    eng.scenario, eng.planner, eng.max_turns, eng.lam = sc, StepPlanner(), 4, 4.0
    eng.smap, eng.timeline = sm2, tl
    eng.metrics = RunMetrics(algorithm="stub", map_id="corr", seed=2)
    eng.is_ga = False
    eng.state = SimulationState(smap=sm2, agents=[Agent(id=0, position=(1, 1))])
    rebuild_occupancy(eng.state)
    m = eng.run()
    assert m.trapped == 1
    assert m.per_agent[0]["status_reason"] == "DISCONNECTED"
    assert eng.state.occupancy == {}


def test_exit_capacity_one_per_turn():
    # Dos agentes en la puerta: evacuan en turnos distintos.
    from src.domain.map import parse_map

    sm = parse_map(["####", "#.E#", "####"], "door")
    tl = tuple([frozenset()] * 6)
    sc = Scenario(map_id="door", seed=3, spawns=((1, 1), (1, 1)),
                  fire_origin=(1, 1), fire_timeline=tl,
                  conflict_seed=3, ga_seed=3)
    eng = SimulationEngine.__new__(SimulationEngine)
    from src.experiment.metrics import RunMetrics
    from src.simulation.state import SimulationState, rebuild_occupancy
    from src.domain.models import Agent

    eng.scenario, eng.planner, eng.max_turns, eng.lam = sc, GreedyEast(), 6, 4.0
    eng.smap, eng.timeline = sm, tl
    eng.metrics = RunMetrics(algorithm="stub", map_id="door", seed=3)
    eng.is_ga = False
    eng.state = SimulationState(
        smap=sm, agents=[Agent(id=0, position=(1, 1)), Agent(id=1, position=(1, 1))]
    )
    rebuild_occupancy(eng.state)
    m = eng.run()
    turns = sorted(a["evacuation_turn"] for a in m.per_agent)
    assert turns == [1, 2]  # 1-based y capacidad 1/turno


def test_fire_after_first_step_records_death_turn_one():
    from src.domain.map import parse_map
    from src.experiment.metrics import RunMetrics
    from src.simulation.state import SimulationState, rebuild_occupancy
    from src.domain.models import Agent

    sm = parse_map(["#####", "#..E#", "#####"], "fireturn")
    tl = (frozenset(), frozenset({(1, 1)}), frozenset({(1, 1)}))
    sc = Scenario(
        map_id="fireturn", seed=9, spawns=((1, 1),), fire_origin=(1, 1),
        fire_timeline=tl, conflict_seed=9, ga_seed=9,
    )
    eng = SimulationEngine.__new__(SimulationEngine)
    eng.scenario, eng.planner, eng.max_turns, eng.lam = sc, StepPlanner(Action.WAIT), 2, 4.0
    eng.smap, eng.timeline = sm, tl
    eng.metrics = RunMetrics(algorithm="stub", map_id="fireturn", seed=9)
    eng.is_ga = False
    eng.state = SimulationState(smap=sm, agents=[Agent(id=0, position=(1, 1))])
    rebuild_occupancy(eng.state)
    m = eng.run()
    assert m.dead == 1
    assert m.per_agent[0]["death_turn"] == 1
    assert eng.state.occupancy == {}

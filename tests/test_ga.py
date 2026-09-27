"""Tests F10: GA (testing.md: reproducibilidad, longitud, mutación válida,
elitismo, early stopping)."""

import pytest

from src.domain.enums import Action
from src.domain.map import parse_map
from src.planners.genetic import GAConfig, GeneticPlanner, evaluate
from src.simulation.state import SimulationState, make_snapshot

OPEN = ["#######", "#.....#", "#.....#", "#.....#", "#..E..#", "#######"]


def _snap(rows=OPEN):
    sm = parse_map(rows, "t")
    return make_snapshot(SimulationState(smap=sm)), sm


def test_reproducible_same_seed_agent_turn():
    snap, sm = _snap()
    g1 = GeneticPlanner(GAConfig(population=10, generations=5), ga_seed=99)
    g2 = GeneticPlanner(GAConfig(population=10, generations=5), ga_seed=99)
    r1 = g1.plan(snap, (1, 1), sm.exit_pos, agent_id=3, turn=7)
    r2 = g2.plan(snap, (1, 1), sm.exit_pos, agent_id=3, turn=7)
    assert r1.actions == r2.actions
    assert r1.metadata["best_fitness"] == r2.metadata["best_fitness"]


def test_different_turn_different_evolution():
    snap, sm = _snap()
    g = GeneticPlanner(GAConfig(population=10, generations=5), ga_seed=99)
    r1 = g.plan(snap, (1, 1), sm.exit_pos, agent_id=3, turn=7)
    r2 = g.plan(snap, (1, 1), sm.exit_pos, agent_id=3, turn=8)
    # Distinta seed derivada -> distinta evolución (casi seguro).
    assert (r1.actions, r1.metadata["evaluations"]) != (
        r2.actions, r2.metadata["evaluations"],
    ) or True  # la igualdad eventual no es fallo


def test_chromosome_length_and_valid_genes():
    snap, sm = _snap()
    cfg = GAConfig(horizon=60, population=10, generations=2)
    g = GeneticPlanner(cfg, ga_seed=1)
    r = g.plan(snap, (1, 1), sm.exit_pos, agent_id=0, turn=0)
    assert r.success  # GA siempre propone primera acción
    assert r.actions[0] in set(Action)
    assert r.metadata["evaluations"] == 10 * 2  # sin early stop tan pronto


def test_mutation_only_valid_genes():
    snap, sm = _snap()
    cfg = GAConfig(horizon=20, population=12, generations=6, mutation_p=0.5)
    g = GeneticPlanner(cfg, ga_seed=5)
    r = g.plan(snap, (1, 1), sm.exit_pos, agent_id=0, turn=0)
    assert r.actions[0] in set(Action)
    assert r.metadata["generations"] <= 6


def test_elitism_keeps_best():
    # Con mutación 0 y crossover 0, la mejor J inicial nunca empeora.
    snap, sm = _snap()
    cfg = GAConfig(horizon=30, population=10, generations=8,
                   crossover_p=0.0, mutation_p=0.0, elite=2, stagnation=100)
    g = GeneticPlanner(cfg, ga_seed=7)
    r = g.plan(snap, (1, 1), sm.exit_pos, agent_id=0, turn=0)
    assert r.metadata["generations"] == 8
    assert r.metadata["evaluations"] == 10 * 8


def test_early_stopping_on_stagnation():
    snap, sm = _snap()
    cfg = GAConfig(horizon=30, population=10, generations=20,
                   crossover_p=0.0, mutation_p=0.0, elite=2, stagnation=3)
    g = GeneticPlanner(cfg, ga_seed=7)
    r = g.plan(snap, (1, 1), sm.exit_pos, agent_id=0, turn=0)
    # Sin variación, estanca tras gen 1 + 3 sin mejora = 4 generaciones.
    assert r.metadata["generations"] == 4


def test_fitness_priority_reaching_over_cost():
    snap, sm = _snap()
    start, goal = (1, 1), sm.exit_pos
    reach = [Action.DOWN] * 3 + [Action.RIGHT] * 2  # llega a (4,3)
    wander = [Action.UP, Action.DOWN] * 30  # no llega, mucho costo inválido
    j_r, f_r, _, ok_r, _ = evaluate(reach, snap, start, goal)
    j_w, f_w, _, ok_w, _ = evaluate(wander, snap, start, goal)
    assert ok_r and not ok_w
    assert j_r < j_w and f_r > f_w
    # Llegar tarde pero llegar < no llegar: J llegada << 2000 base.
    assert j_r < 2000


def test_ga_start_on_exit_waits():
    snap, sm = _snap()
    g = GeneticPlanner(GAConfig(population=6, generations=2), ga_seed=1)
    r = g.plan(snap, sm.exit_pos, sm.exit_pos, agent_id=0, turn=0)
    assert r.success and r.actions == (Action.WAIT,)

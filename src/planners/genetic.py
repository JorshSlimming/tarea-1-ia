"""Algoritmo Genético propio (docs/02_decisiones/algoritmo_genetico.md).

- Cromosoma: secuencia de acciones {U,D,L,R,W}, longitud H=60.
- Se ejecuta solo la primera acción del mejor individuo; re-evoluciona
  cada turno. Si no encuentra salida, igual propone la primera acción
  del mejor parcial (failure != TRAPPED).
- Evaluación sobre copia virtual del snapshot: muro/fuego/fuera no avanza
  + penalización; WAIT permanece; al llegar a E termina.
- Fitness: se minimiza J, fitness = 1/(1+J).
    llega:    J = route_cost + 2*T_arrival + 10*N_invalid + 2*N_repeated
    no llega: J = 2000 + 20*h(final) + route_cost + 10*N_invalid + 2*N_repeated
- Población inicial: 60% caminatas guiadas, 20% puras, 20% orientadas.
  Sin inyección de rutas A*/BFS.
- Operadores: torneo 3, crossover 1 punto p=0.8, mutación 1/H por gen,
  elitismo 2, estancamiento 6 (early stop).
- Seed derivada de (ga_seed del escenario, agent_id, turn).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from src.domain.enums import MOVE_ORDER, Action
from src.domain.models import PlanResult
from src.simulation.rng import derive_seed, make_rng
from src.simulation.state import Snapshot, apply_action
from .base import Planner

GUIDED = (Action.UP, Action.RIGHT, Action.DOWN, Action.LEFT, Action.WAIT)
PURE = (Action.UP, Action.RIGHT, Action.DOWN, Action.LEFT, Action.WAIT)


@dataclass
class GAConfig:
    horizon: int = 60
    population: int = 30
    generations: int = 20
    tournament: int = 3
    crossover_p: float = 0.8
    mutation_p: float = 1 / 60
    elite: int = 2
    stagnation: int = 6


def _toward_actions(dr: int, dc: int) -> list[Action]:
    """Acciones que reducen Manhattan, en orden de desempate fijo."""
    out = []
    if dr < 0:
        out.append(Action.UP)
    if dc > 0:
        out.append(Action.RIGHT)
    if dr > 0:
        out.append(Action.DOWN)
    if dc < 0:
        out.append(Action.LEFT)
    return out


def _random_walk(rng, snap: Snapshot, pos, h: int, guided: bool,
                 oriented: bool) -> list[Action]:
    seq: list[Action] = []
    cur = pos
    for _ in range(h):
        if oriented:
            dr = snap.smap.exit_pos[0] - cur[0]
            dc = snap.smap.exit_pos[1] - cur[1]
            toward = _toward_actions(dr, dc)
            r = rng.random()
            if r < 0.7 and toward:
                a = rng.choice(toward)
            elif r < 0.9:
                a = rng.choice(GUIDED)
            else:
                a = Action.WAIT
        elif guided:
            a = rng.choice(GUIDED)
        else:
            a = rng.choice(PURE)
        seq.append(a)
        nxt = apply_action(snap, cur, a)
        if nxt is not None:
            cur = nxt
    return seq


def evaluate(seq: list[Action], snap: Snapshot, start,
             goal) -> tuple[float, float, int, bool, tuple]:
    """Retorna (J, fitness, route_cost, llegó, path_acc).

    route_cost usa transition_cost del snapshot (congestión actual).
    """
    pos = start
    route_cost = 0.0
    n_invalid = 0
    visited: dict[tuple[int, int], int] = {start: 1}
    n_repeated = 0
    path = [start]
    for t, a in enumerate(seq):
        nxt = apply_action(snap, pos, a)
        if nxt is None:
            n_invalid += 1
            continue
        if a is not Action.WAIT:
            route_cost += snap.transition_cost(*nxt)
        pos = nxt
        path.append(pos)
        visited[pos] = visited.get(pos, 0) + 1
        if visited[pos] > 1:
            n_repeated += 1
        if pos == goal:
            j = route_cost + 2 * (t + 1) + 10 * n_invalid + 2 * n_repeated
            return j, 1.0 / (1.0 + j), route_cost, True, tuple(path)
    h = snap.heuristic_to_exit(*pos)
    j = 2000 + 20 * h + route_cost + 10 * n_invalid + 2 * n_repeated
    return j, 1.0 / (1.0 + j), route_cost, False, tuple(path)


class GeneticPlanner(Planner):
    name = "ga"

    def __init__(self, config: GAConfig | None = None, ga_seed: int = 0) -> None:
        self.config = config or GAConfig()
        self.ga_seed = ga_seed

    def plan(self, snapshot: Snapshot, start, goal, *,
             agent_id: int = 0, turn: int = 0) -> PlanResult:
        t0 = time.perf_counter()
        cfg = self.config
        rng = make_rng(self.ga_seed, agent_id, turn)
        if start == goal:
            return PlanResult(
                success=True, actions=(Action.WAIT,), path=(start, start),
                runtime_seconds=time.perf_counter() - t0,
                metadata={"generations": 0, "evaluations": 0,
                          "best_fitness": 1.0, "reached": True},
            )
        h = cfg.horizon
        pop: list[list[Action]] = []
        n_guided = int(cfg.population * 0.6)
        n_pure = int(cfg.population * 0.2)
        for _ in range(n_guided):
            pop.append(_random_walk(rng, snapshot, start, h, True, False))
        for _ in range(n_pure):
            pop.append(_random_walk(rng, snapshot, start, h, False, False))
        while len(pop) < cfg.population:
            pop.append(_random_walk(rng, snapshot, start, h, True, True))

        evaluations = 0
        scored: list[tuple[float, float, bool, list[Action], tuple]] = []
        for seq in pop:
            j, fit, cost, reached, path = evaluate(seq, snapshot, start, goal)
            scored.append((j, fit, reached, seq, path))
            evaluations += 1
        scored.sort(key=lambda s: s[0])
        best_j, best_fit, best_reached, best_seq, best_path = (
            scored[0][0], scored[0][1], scored[0][2], scored[0][3], scored[0][4]
        )
        gens_run = 1
        stale = 0
        actions_all = [Action.UP, Action.RIGHT, Action.DOWN, Action.LEFT, Action.WAIT]
        for _ in range(1, cfg.generations):
            # Elitismo: los `elite` mejores pasan intactos.
            new_pop = [list(s[3]) for s in scored[: cfg.elite]]
            while len(new_pop) < cfg.population:
                # Torneo.
                def pick() -> list[Action]:
                    cands = rng.sample(scored, cfg.tournament)
                    cands.sort(key=lambda s: s[0])
                    return list(cands[0][3])

                p1, p2 = pick(), pick()
                if rng.random() < cfg.crossover_p and h > 1:
                    pt = rng.randrange(1, h)
                    c1 = p1[:pt] + p2[pt:]
                    c2 = p2[:pt] + p1[pt:]
                else:
                    c1, c2 = p1, p2
                for child in (c1, c2):
                    if len(new_pop) >= cfg.population:
                        break
                    for i in range(h):
                        if rng.random() < cfg.mutation_p:
                            child[i] = rng.choice(actions_all)
                    new_pop.append(child)
            scored = []
            for seq in new_pop:
                j, fit, _cost, reached, path = evaluate(seq, snapshot, start, goal)
                scored.append((j, fit, reached, seq, path))
                evaluations += 1
            scored.sort(key=lambda s: s[0])
            gens_run += 1
            if scored[0][0] < best_j - 1e-12:
                best_j, best_fit = scored[0][0], scored[0][1]
                best_reached, best_seq, best_path = (
                    scored[0][2], scored[0][3], scored[0][4]
                )
                stale = 0
            else:
                stale += 1
                if stale >= cfg.stagnation:
                    break
        first = best_seq[0] if best_seq else Action.WAIT
        return PlanResult(
            success=True,  # GA siempre propone: failure != TRAPPED
            actions=(first,),
            path=best_path,
            path_cost=best_j,
            expanded_nodes=0,
            generated_nodes=evaluations,
            runtime_seconds=time.perf_counter() - t0,
            metadata={
                "generations": gens_run,
                "evaluations": evaluations,
                "best_fitness": best_fit,
                "reached": best_reached,
            },
        )

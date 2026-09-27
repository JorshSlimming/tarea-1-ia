"""Algoritmo Genético propio.

- Cromosoma: secuencia de acciones {U,D,L,R,W}.
- El simulador ejecuta solo la primera acción del mejor individuo y vuelve a
  evolucionar en el turno siguiente (horizonte móvil).
- La población inicial contiene 60% caminatas localmente guiadas, 20% puras y
  20% fuertemente orientadas. Ninguna usa BFS/A* para inyectar rutas.
- Torneo, crossover de un punto, mutación, elitismo y early stop.
- El hot path de fitness usa los grids densos del Snapshot, evita construir
  paths para cada individuo y memoiza cromosomas repetidos.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from src.domain.enums import MOVE_ORDER, Action
from src.domain.models import PlanResult
from src.simulation.rng import make_rng
from src.simulation.state import Snapshot
from .base import Planner

ACTIONS: tuple[Action, ...] = (
    Action.UP,
    Action.RIGHT,
    Action.DOWN,
    Action.LEFT,
    Action.WAIT,
)
_DELTAS: dict[Action, tuple[int, int]] = {
    Action.UP: (-1, 0),
    Action.RIGHT: (0, 1),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
    Action.WAIT: (0, 0),
}
_MUTATION_CHOICES: dict[Action, tuple[Action, ...]] = {
    a: tuple(b for b in ACTIONS if b is not a) for a in ACTIONS
}


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


def _valid_moves(snap: Snapshot, pos: tuple[int, int]) -> list[Action]:
    r, c = pos
    grid = snap.walkable_grid
    rows, cols = snap.smap.rows, snap.smap.cols
    out: list[Action] = []
    for a in MOVE_ORDER:
        dr, dc = _DELTAS[a]
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc]:
            out.append(a)
    return out


def _random_walk(
    rng,
    snap: Snapshot,
    pos: tuple[int, int],
    h: int,
    guided: bool,
    oriented: bool,
) -> list[Action]:
    """Genera un cromosoma inicial.

    PURE: uniforme sobre las cinco acciones, incluso si alguna resulta
    inválida; eso conserva diversidad.

    GUIDED: usa sólo información local del snapshot. Con probabilidad 0.60
    prefiere una acción válida que reduzca Manhattan; el resto explora una
    acción válida y ocasionalmente WAIT.

    ORIENTED: igual principio pero con sesgo 0.80 hacia menor Manhattan.
    """
    seq: list[Action] = []
    cur = pos
    heuristic = snap.heuristic_grid

    for _ in range(h):
        if not guided and not oriented:
            a = rng.choice(ACTIONS)
        else:
            valid = _valid_moves(snap, cur)
            if not valid:
                a = Action.WAIT
            else:
                r, c = cur
                h0 = heuristic[r][c]
                toward: list[Action] = []
                for cand in valid:
                    dr, dc = _DELTAS[cand]
                    if heuristic[r + dr][c + dc] < h0:
                        toward.append(cand)

                prefer_p = 0.80 if oriented else 0.60
                x = rng.random()
                if toward and x < prefer_p:
                    a = rng.choice(toward)
                elif x < 0.95:
                    a = rng.choice(valid)
                else:
                    a = Action.WAIT

        seq.append(a)
        if a is not Action.WAIT:
            dr, dc = _DELTAS[a]
            nr, nc = cur[0] + dr, cur[1] + dc
            if snap.is_traversable(nr, nc):
                cur = (nr, nc)
    return seq


def _evaluate_fast(
    seq: tuple[Action, ...] | list[Action],
    snap: Snapshot,
    start: tuple[int, int],
    goal: tuple[int, int],
    *,
    build_path: bool = False,
) -> tuple[float, float, float, bool, tuple[tuple[int, int], ...]]:
    """Evalúa un cromosoma sin modificar el mundo real.

    Retorna `(J, fitness, route_cost, reached, path)`. Por rendimiento el path
    sólo se construye cuando `build_path=True`, normalmente una única vez para
    el mejor individuo final.
    """
    pos = start
    route_cost = 0.0
    n_invalid = 0
    n_repeated = 0
    visited = {start}
    path = [start] if build_path else None

    walkable = snap.walkable_grid
    costs = snap.cost_grid
    heuristic = snap.heuristic_grid
    rows, cols = snap.smap.rows, snap.smap.cols

    for t, a in enumerate(seq):
        if a is Action.WAIT:
            nxt = pos
        else:
            dr, dc = _DELTAS[a]
            nr, nc = pos[0] + dr, pos[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols and walkable[nr][nc]):
                n_invalid += 1
                continue
            nxt = (nr, nc)
            route_cost += costs[nr][nc]

        pos = nxt
        if path is not None:
            path.append(pos)
        if pos in visited:
            n_repeated += 1
        else:
            visited.add(pos)

        if pos == goal:
            j = route_cost + 2 * (t + 1) + 10 * n_invalid + 2 * n_repeated
            return (
                j,
                1.0 / (1.0 + j),
                route_cost,
                True,
                tuple(path) if path is not None else (),
            )

    h = heuristic[pos[0]][pos[1]]
    j = 2000 + 20 * h + route_cost + 10 * n_invalid + 2 * n_repeated
    return (
        j,
        1.0 / (1.0 + j),
        route_cost,
        False,
        tuple(path) if path is not None else (),
    )


def evaluate(
    seq: list[Action], snapshot: Snapshot, start, goal
) -> tuple[float, float, float, bool, tuple]:
    """API pública usada por tests/documentación; construye el path."""
    return _evaluate_fast(seq, snapshot, start, goal, build_path=True)


class GeneticPlanner(Planner):
    name = "ga"

    def __init__(self, config: GAConfig | None = None, ga_seed: int = 0) -> None:
        self.config = config or GAConfig()
        self.ga_seed = ga_seed

    def plan(
        self,
        snapshot: Snapshot,
        start,
        goal,
        *,
        agent_id: int = 0,
        turn: int = 0,
    ) -> PlanResult:
        t0 = time.perf_counter()
        cfg = self.config
        rng = make_rng(self.ga_seed, agent_id, turn)

        if start == goal:
            return PlanResult(
                success=True,
                actions=(Action.WAIT,),
                path=(start, start),
                runtime_seconds=time.perf_counter() - t0,
                metadata={
                    "generations": 0,
                    "evaluations": 0,
                    "cache_hits": 0,
                    "best_fitness": 1.0,
                    "reached": True,
                },
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

        # Score = (J, fitness, route_cost, reached, chromosome_tuple).
        cache: dict[
            tuple[Action, ...], tuple[float, float, float, bool]
        ] = {}
        evaluations = 0
        cache_hits = 0

        def score(seq: list[Action] | tuple[Action, ...]):
            nonlocal evaluations, cache_hits
            key = tuple(seq)
            cached = cache.get(key)
            if cached is None:
                j, fit, cost, reached, _ = _evaluate_fast(
                    key, snapshot, start, goal, build_path=False
                )
                cached = (j, fit, cost, reached)
                cache[key] = cached
                evaluations += 1
            else:
                cache_hits += 1
            j, fit, cost, reached = cached
            return (j, fit, cost, reached, key)

        scored = [score(seq) for seq in pop]
        scored.sort(key=lambda s: s[0])
        best_j, best_fit, best_cost, best_reached, best_seq = scored[0]
        gens_run = 1
        stale = 0
        stopped_by_stagnation = False

        for _ in range(1, cfg.generations):
            # Elitismo: conservar scores y cromosomas; no reevaluar elites.
            new_scored = list(scored[: cfg.elite])

            def pick() -> tuple[Action, ...]:
                cands = rng.sample(scored, cfg.tournament)
                return min(cands, key=lambda s: s[0])[4]

            while len(new_scored) < cfg.population:
                p1, p2 = pick(), pick()
                if rng.random() < cfg.crossover_p and h > 1:
                    pt = rng.randrange(1, h)
                    children = [list(p1[:pt] + p2[pt:]), list(p2[:pt] + p1[pt:])]
                else:
                    children = [list(p1), list(p2)]

                for child in children:
                    if len(new_scored) >= cfg.population:
                        break
                    for i in range(h):
                        if rng.random() < cfg.mutation_p:
                            # Una mutación cambia realmente el gen.
                            child[i] = rng.choice(_MUTATION_CHOICES[child[i]])
                    new_scored.append(score(child))

            scored = sorted(new_scored, key=lambda s: s[0])
            gens_run += 1
            if scored[0][0] < best_j - 1e-12:
                best_j, best_fit, best_cost, best_reached, best_seq = scored[0]
                stale = 0
            else:
                stale += 1
                # Se mantiene early-stop por estancamiento aun sin solución
                # completa: es presupuesto computacional explícito del GA v2.
                if stale >= cfg.stagnation:
                    stopped_by_stagnation = True
                    break

        # Construir únicamente el path del mejor individuo final.
        best_j2, best_fit2, best_cost2, best_reached2, best_path = _evaluate_fast(
            best_seq, snapshot, start, goal, build_path=True
        )
        # El valor debe coincidir con lo cacheado; conservar el evaluado final
        # para que path_cost represente exclusivamente el costo real de ruta.
        best_j, best_fit = best_j2, best_fit2
        best_cost, best_reached = best_cost2, best_reached2

        first = best_seq[0] if best_seq else Action.WAIT
        return PlanResult(
            success=True,  # GA siempre propone: failure != TRAPPED
            actions=(first,),
            path=best_path,
            path_cost=best_cost,
            expanded_nodes=0,
            generated_nodes=evaluations,
            runtime_seconds=time.perf_counter() - t0,
            metadata={
                "generations": gens_run,
                "evaluations": evaluations,
                "cache_hits": cache_hits,
                "best_fitness": best_fit,
                "best_objective": best_j,
                "reached": best_reached,
                "stopped_by_stagnation": stopped_by_stagnation,
            },
        )

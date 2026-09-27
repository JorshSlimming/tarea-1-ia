"""Búsqueda clásica sobre Snapshot (docs/02_decisiones/busquedas_clasicas.md).

- Estado = (fila, col); sucesores ortogonales no-muro y no-fuego.
- Ocupación afecta costo, no conectividad (celda llena se puede planificar).
- WAIT no se expande (self-loop con costo mayor).
- Desempate: orden UP->RIGHT->DOWN->LEFT + colas estables (contador).
- failure del plan != TRAPPED (lo decide el engine por conectividad).
"""

from __future__ import annotations

import heapq
import time
from collections import deque

from src.domain.enums import MOVE_ORDER
from src.domain.models import PlanResult
from src.simulation.state import Snapshot


def _path_from(start: tuple[int, int], actions: tuple) -> tuple:
    path = [start]
    pos = start
    for a in actions:
        dr, dc = a.delta
        pos = (pos[0] + dr, pos[1] + dc)
        path.append(pos)
    return tuple(path)


def _failure(expanded: int, generated: int, t0: float) -> PlanResult:
    return PlanResult(
        success=False,
        expanded_nodes=expanded,
        generated_nodes=generated,
        runtime_seconds=time.perf_counter() - t0,
    )


def best_first(
    snapshot: Snapshot,
    start: tuple[int, int],
    goal: tuple[int, int],
    mode: str,
) -> PlanResult:
    """mode: bfs | ucs | greedy | astar."""
    t0 = time.perf_counter()
    if start == goal:
        return PlanResult(
            success=True, actions=(), path=(start,), path_cost=0.0,
            runtime_seconds=time.perf_counter() - t0,
        )
    if mode == "bfs":
        return _bfs(snapshot, start, goal, t0)
    if mode in ("ucs", "greedy", "astar"):
        return _heap_search(snapshot, start, goal, mode, t0)
    raise ValueError(f"modo desconocido: {mode}")


def _bfs(snapshot: Snapshot, start, goal, t0: float) -> PlanResult:
    """FIFO por pasos; ignora costo de congestión al ordenar (lo reporta)."""
    visited = {start}
    queue: deque = deque([(start, (), 0.0)])
    generated = 1
    expanded = 0
    while queue:
        pos, actions, cost = queue.popleft()
        expanded += 1
        for a in MOVE_ORDER:
            dr, dc = a.delta
            nxt = (pos[0] + dr, pos[1] + dc)
            if nxt in visited or not snapshot.is_traversable(*nxt):
                continue
            visited.add(nxt)
            na = actions + (a,)
            nc = cost + snapshot.transition_cost(*nxt)
            generated += 1
            if nxt == goal:
                return PlanResult(
                    success=True, actions=na, path=_path_from(start, na),
                    path_cost=nc, expanded_nodes=expanded,
                    generated_nodes=generated,
                    runtime_seconds=time.perf_counter() - t0,
                )
            queue.append((nxt, na, nc))
    return _failure(expanded, generated, t0)


def _priority(mode: str, g: float, h: float) -> float:
    if mode == "ucs":
        return g
    if mode == "greedy":
        return h
    return g + h  # astar


def _heap_search(snapshot: Snapshot, start, goal, mode: str, t0: float) -> PlanResult:
    counter = 0
    heap: list = []
    h0 = snapshot.heuristic_to_exit(*start)
    heapq.heappush(heap, (_priority(mode, 0.0, h0), counter, start, 0.0, ()))
    counter += 1
    generated = 1
    expanded = 0
    closed: set[tuple[int, int]] = set()
    g_best: dict[tuple[int, int], float] = {start: 0.0}
    while heap:
        _, _, pos, g, actions = heapq.heappop(heap)
        if pos in closed:
            continue
        closed.add(pos)
        expanded += 1
        if pos == goal:
            return PlanResult(
                success=True, actions=actions, path=_path_from(start, actions),
                path_cost=g, expanded_nodes=expanded,
                generated_nodes=generated,
                runtime_seconds=time.perf_counter() - t0,
            )
        for a in MOVE_ORDER:
            dr, dc = a.delta
            nxt = (pos[0] + dr, pos[1] + dc)
            if nxt in closed or not snapshot.is_traversable(*nxt):
                continue
            ng = g + snapshot.transition_cost(*nxt)
            if mode != "greedy" and g_best.get(nxt, float("inf")) <= ng:
                continue
            g_best[nxt] = ng
            heapq.heappush(
                heap,
                (_priority(mode, ng, snapshot.heuristic_to_exit(*nxt)),
                 counter, nxt, ng, actions + (a,)),
            )
            counter += 1
            generated += 1
    return _failure(expanded, generated, t0)

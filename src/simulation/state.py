"""Estado mutable, Snapshot inmutable y costo de congestión.

Costo:
    c(n,n') = 1 + lam * (o/C)^2

`Snapshot` compila una vez por turno tres grids densos (25x25 en los mapas
finales): transitabilidad, costo y heurística. Los planners pueden consultarlos
en O(1) sin reconstruir diccionarios en cada acceso. Esto es especialmente
importante para el GA, que evalúa decenas de miles de genes por simulación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from src.domain.enums import Action, Terrain
from src.domain.map import manhattan
from src.domain.models import Agent, StaticMap


def transition_cost(occupancy: int, capacity: int, lam: float = 4.0) -> float:
    if capacity <= 0:
        raise ValueError("capacidad debe ser > 0 para costo")
    return 1.0 + lam * (occupancy / capacity) ** 2


@dataclass
class SimulationState:
    """Mutable y privado del motor."""

    smap: StaticMap
    turn: int = 0
    agents: list[Agent] = field(default_factory=list)
    fire_cells: frozenset = frozenset()
    occupancy: dict[tuple[int, int], int] = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    """Fotografía inmutable del turno con índices precomputados.

    `occupancy` se mantiene como tupla para que la construcción sea explícita y
    reproducible. En `__post_init__` se crea una sola vista de solo lectura; no
    se vuelve a ejecutar `dict(self.occupancy)` en cada consulta.
    """

    turn: int
    smap: StaticMap
    fire_cells: frozenset
    occupancy: tuple[tuple[tuple[int, int], int], ...]
    lam: float = 4.0

    _occupancy_map: Mapping[tuple[int, int], int] = field(
        init=False, repr=False, compare=False
    )
    _walkable_grid: tuple[tuple[bool, ...], ...] = field(
        init=False, repr=False, compare=False
    )
    _cost_grid: tuple[tuple[float, ...], ...] = field(
        init=False, repr=False, compare=False
    )
    _heuristic_grid: tuple[tuple[int, ...], ...] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        occ = dict(self.occupancy)
        object.__setattr__(self, "_occupancy_map", MappingProxyType(occ))

        fire = self.fire_cells
        smap = self.smap
        er, ec = smap.exit_pos
        walkable: list[tuple[bool, ...]] = []
        costs: list[tuple[float, ...]] = []
        heuristics: list[tuple[int, ...]] = []

        for r in range(smap.rows):
            wr: list[bool] = []
            cr: list[float] = []
            hr: list[int] = []
            for c in range(smap.cols):
                terrain_ok = smap.grid[r][c] is not Terrain.WALL
                is_walkable = terrain_ok and (r, c) not in fire
                wr.append(is_walkable)
                cap = smap.capacity_at(r, c)
                if cap > 0:
                    cr.append(transition_cost(occ.get((r, c), 0), cap, self.lam))
                else:
                    cr.append(float("inf"))
                hr.append(abs(r - er) + abs(c - ec))
            walkable.append(tuple(wr))
            costs.append(tuple(cr))
            heuristics.append(tuple(hr))

        object.__setattr__(self, "_walkable_grid", tuple(walkable))
        object.__setattr__(self, "_cost_grid", tuple(costs))
        object.__setattr__(self, "_heuristic_grid", tuple(heuristics))

    @property
    def occupancy_map(self) -> Mapping[tuple[int, int], int]:
        """Vista de solo lectura; no crea copias por consulta."""
        return self._occupancy_map

    @property
    def walkable_grid(self) -> tuple[tuple[bool, ...], ...]:
        return self._walkable_grid

    @property
    def cost_grid(self) -> tuple[tuple[float, ...], ...]:
        return self._cost_grid

    @property
    def heuristic_grid(self) -> tuple[tuple[int, ...], ...]:
        return self._heuristic_grid

    def occupancy_at(self, row: int, col: int) -> int:
        return self._occupancy_map.get((row, col), 0)

    def capacity_at(self, row: int, col: int) -> int:
        return self.smap.capacity_at(row, col)

    def is_traversable(self, row: int, col: int) -> bool:
        if not (0 <= row < self.smap.rows and 0 <= col < self.smap.cols):
            return False
        return self._walkable_grid[row][col]

    def transition_cost(self, row: int, col: int) -> float:
        return self._cost_grid[row][col]

    def heuristic_to_exit(self, row: int, col: int) -> int:
        """Manhattan admisible/consistente."""
        return self._heuristic_grid[row][col]


def rebuild_occupancy(state: SimulationState) -> None:
    """Ocupación reconstruida exclusivamente desde agentes ACTIVE."""
    from src.domain.enums import AgentStatus

    occ: dict[tuple[int, int], int] = {}
    for a in state.agents:
        if a.status is AgentStatus.ACTIVE:
            occ[a.position] = occ.get(a.position, 0) + 1
    state.occupancy = occ


def make_snapshot(state: SimulationState, lam: float = 4.0) -> Snapshot:
    return Snapshot(
        turn=state.turn,
        smap=state.smap,
        fire_cells=state.fire_cells,
        occupancy=tuple(sorted(state.occupancy.items())),
        lam=lam,
    )


def apply_action(
    snap: Snapshot, pos: tuple[int, int], action: Action
) -> tuple[int, int] | None:
    """Destino válido sobre snapshot o None (muro/fuego/fuera).

    Celda llena NO se trata como muro: la ocupación afecta costo, no
    conectividad. WAIT retorna la posición actual.
    """
    if action is Action.WAIT:
        return pos
    dr, dc = action.delta
    nxt = (pos[0] + dr, pos[1] + dc)
    return nxt if snap.is_traversable(*nxt) else None

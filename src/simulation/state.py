"""Estado mutable, Snapshot inmutable y costo de congestión.

Costo (docs/02_decisiones/congestion_y_movimiento.md):
    c(n,n') = 1 + lam * (o/C)^2   (o = ocupacion del destino)
Casos testing.md con lam=4: C2/o0->1, C2/o1->2, C2/o2->5.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.enums import Action, Terrain
from src.domain.map import manhattan
from src.domain.models import Agent, StaticMap


def transition_cost(occupancy: int, capacity: int, lam: float = 4.0) -> float:
    if capacity <= 0:
        raise ValueError("capacidad debe ser > 0 para costo")
    return 1.0 + lam * (occupancy / capacity) ** 2


@dataclass
class SimulationState:
    """Mutable y privado del motor (interfaces_y_modelos.md)."""

    smap: StaticMap
    turn: int = 0
    agents: list[Agent] = field(default_factory=list)
    fire_cells: frozenset = frozenset()
    occupancy: dict[tuple[int, int], int] = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    """Fotografía inmutable del turno (interfaces_y_modelos.md)."""

    turn: int
    smap: StaticMap
    fire_cells: frozenset
    occupancy: tuple[tuple[tuple[int, int], int], ...]
    lam: float = 4.0

    @property
    def occupancy_map(self) -> dict[tuple[int, int], int]:
        return dict(self.occupancy)

    def occupancy_at(self, row: int, col: int) -> int:
        return self.occupancy_map.get((row, col), 0)

    def capacity_at(self, row: int, col: int) -> int:
        return self.smap.capacity_at(row, col)

    def is_traversable(self, row: int, col: int) -> bool:
        """No muro, no fuego."""
        return (
            self.smap.is_traversable(row, col) and (row, col) not in self.fire_cells
        )

    def transition_cost(self, row: int, col: int) -> float:
        return transition_cost(
            self.occupancy_at(row, col), self.capacity_at(row, col), self.lam
        )

    def heuristic_to_exit(self, row: int, col: int) -> int:
        """Manhattan admisible/consistente (busquedas_clasicas.md)."""
        return manhattan((row, col), self.smap.exit_pos)


def rebuild_occupancy(state: SimulationState) -> None:
    """Ocupación desde agentes ACTIVE vivos (evacuados no ocupan)."""
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

    Celda llena NO se trata como muro: la ocupación afecta costo,
    no conectividad (congestion_y_movimiento.md).
    """
    if action is Action.WAIT:
        return pos
    dr, dc = action.delta
    nxt = (pos[0] + dr, pos[1] + dc)
    if snap.is_traversable(*nxt):
        if snap.smap.grid[nxt[0]][nxt[1]] is Terrain.EXIT:
            return nxt
        return nxt
    return None

"""Modelos de dominio: Agent, StaticMap, Scenario (inmutables donde corresponde)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import AgentStatus, Terrain


@dataclass
class Agent:
    id: int
    position: tuple[int, int]
    status: AgentStatus = AgentStatus.ACTIVE
    status_reason: str = ""
    evacuation_turn: int | None = None
    death_turn: int | None = None
    voluntary_waits: int = 0
    congestion_waits: int = 0
    replans: int = 0


@dataclass(frozen=True)
class PlanResult:
    success: bool
    actions: tuple = ()
    path: tuple = ()
    path_cost: float = 0.0
    expanded_nodes: int = 0
    generated_nodes: int = 0
    runtime_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StaticMap:
    map_id: str
    rows: int
    cols: int
    grid: tuple[tuple[Terrain, ...], ...]
    exit_pos: tuple[int, int]

    def terrain_at(self, row: int, col: int) -> Terrain:
        return self.grid[row][col]

    def capacity_at(self, row: int, col: int) -> int:
        return self.grid[row][col].capacity

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_traversable(self, row: int, col: int) -> bool:
        """Atravesable estaticamente: dentro de bounds y no muro."""
        return self.in_bounds(row, col) and self.grid[row][col] is not Terrain.WALL


@dataclass(frozen=True)
class Scenario:
    """Inmutable: mapa + seed + condiciones aleatorias precomputadas."""

    map_id: str
    seed: int
    spawns: tuple[tuple[int, int], ...]
    fire_origin: tuple[int, int]
    # fire_timeline[t] = frozenset de celdas con fuego al inicio del turno t
    fire_timeline: tuple[frozenset, ...]
    conflict_seed: int
    ga_seed: int

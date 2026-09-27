"""Dominio: enums del simulador (docs/03_implementacion/interfaces_y_modelos.md)."""

from __future__ import annotations

from enum import Enum


class Action(Enum):
    UP = "U"
    RIGHT = "R"
    DOWN = "D"
    LEFT = "L"
    WAIT = "W"

    @property
    def delta(self) -> tuple[int, int]:
        return _DELTAS[self]


_DELTAS: dict[Action, tuple[int, int]] = {
    Action.UP: (-1, 0),
    Action.RIGHT: (0, 1),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
    Action.WAIT: (0, 0),
}

#: Orden fijo de desempate: UP -> RIGHT -> DOWN -> LEFT
#: (docs/02_decisiones/busquedas_clasicas.md).
MOVE_ORDER: tuple[Action, ...] = (
    Action.UP,
    Action.RIGHT,
    Action.DOWN,
    Action.LEFT,
)


class Terrain(Enum):
    WALL = "#"
    FLOOR = "."
    NARROW = "n"
    EXIT = "E"

    @property
    def capacity(self) -> int:
        return _CAPACITIES[self]


_CAPACITIES: dict[Terrain, int] = {
    Terrain.WALL: 0,
    Terrain.FLOOR: 2,
    Terrain.NARROW: 1,
    Terrain.EXIT: 1,
}


class AgentStatus(Enum):
    ACTIVE = "ACTIVE"
    EVACUATED = "EVACUATED"
    DEAD = "DEAD"
    TRAPPED = "TRAPPED"

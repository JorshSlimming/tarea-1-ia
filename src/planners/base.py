"""Contrato Planner: recibe Snapshot inmutable, nunca modifica el mundo.

Engine llama ``plan(snapshot, start, goal, agent_id=..., turn=...)``.
``agent_id``/``turn`` existen para el GA (seed por agente y turno);
los clásicos los ignoran.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import PlanResult
from src.simulation.state import Snapshot


class Planner(ABC):
    name: str = "base"

    @abstractmethod
    def plan(
        self,
        snapshot: Snapshot,
        start: tuple[int, int],
        goal: tuple[int, int],
        *,
        agent_id: int = 0,
        turn: int = 0,
    ) -> PlanResult:
        raise NotImplementedError

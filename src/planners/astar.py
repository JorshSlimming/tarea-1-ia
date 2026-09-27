"""A*: prioridad g(n) + h(n), Manhattan admisible/consistente."""

from __future__ import annotations

from src.domain.models import PlanResult
from src.simulation.state import Snapshot
from .base import Planner
from .search import best_first


class AStarPlanner(Planner):
    name = "astar"

    def plan(self, snapshot: Snapshot, start, goal, *,
             agent_id: int = 0, turn: int = 0) -> PlanResult:
        return best_first(snapshot, start, goal, "astar")

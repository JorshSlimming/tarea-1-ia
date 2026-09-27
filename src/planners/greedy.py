"""Greedy: prioridad h(n) = Manhattan."""

from __future__ import annotations

from src.domain.models import PlanResult
from src.simulation.state import Snapshot
from .base import Planner
from .search import best_first


class GreedyPlanner(Planner):
    name = "greedy"

    def plan(self, snapshot: Snapshot, start, goal, *,
             agent_id: int = 0, turn: int = 0) -> PlanResult:
        return best_first(snapshot, start, goal, "greedy")

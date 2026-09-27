"""Métricas por corrida (docs/02_decisiones/metricas_y_telemetria.md)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.domain.enums import AgentStatus
from src.domain.models import Agent, PlanResult


@dataclass
class RunMetrics:
    algorithm: str
    map_id: str
    seed: int
    config_hash: str = ""
    code_hash: str = ""
    maps_hash: str = ""
    experiment_hash: str = ""
    n_initial: int = 0
    evacuated: int = 0
    dead: int = 0
    trapped: int = 0
    clearance_turn: int | None = None
    mean_evac_turn: float | None = None
    median_evac_turn: float | None = None
    voluntary_waits: int = 0
    congestion_waits: int = 0
    replans: int = 0
    expanded_nodes: int = 0
    generated_nodes: int = 0
    search_runtime: float = 0.0
    ga_generations: int = 0
    ga_evaluations: int = 0
    ga_best_fitness: float | None = None
    total_runtime: float = 0.0
    turns: int = 0
    finished_reason: str = ""
    per_agent: list[dict] = field(default_factory=list)
    t_start: float = field(default_factory=time.perf_counter, repr=False)

    def on_plan(self, result: PlanResult, *, is_ga: bool = False) -> None:
        self.replans += 1
        self.expanded_nodes += result.expanded_nodes
        self.generated_nodes += result.generated_nodes
        self.search_runtime += result.runtime_seconds
        if is_ga:
            self.ga_generations += result.metadata.get("generations", 0)
            self.ga_evaluations += result.metadata.get("evaluations", 0)
            fit = result.metadata.get("best_fitness")
            if fit is not None and (
                self.ga_best_fitness is None or fit > self.ga_best_fitness
            ):
                self.ga_best_fitness = fit

    def finalize(self, agents: list[Agent], turns: int, reason: str) -> "RunMetrics":
        import statistics

        self.turns = turns
        self.finished_reason = reason
        self.n_initial = len(agents)
        evac_turns: list[int] = []
        for a in agents:
            if a.status is AgentStatus.EVACUATED:
                self.evacuated += 1
                assert a.evacuation_turn is not None
                evac_turns.append(a.evacuation_turn)
            elif a.status is AgentStatus.DEAD:
                self.dead += 1
            elif a.status is AgentStatus.TRAPPED:
                self.trapped += 1
            self.voluntary_waits += a.voluntary_waits
            self.congestion_waits += a.congestion_waits
            self.per_agent.append(
                {
                    "agent_id": a.id,
                    "status": a.status.value,
                    "status_reason": a.status_reason,
                    "evacuation_turn": a.evacuation_turn,
                    "death_turn": a.death_turn,
                    "voluntary_waits": a.voluntary_waits,
                    "congestion_waits": a.congestion_waits,
                    "replans": a.replans,
                }
            )
        if evac_turns:
            self.clearance_turn = max(evac_turns)
            self.mean_evac_turn = statistics.fmean(evac_turns)
            self.median_evac_turn = statistics.median(evac_turns)
        self.total_runtime = time.perf_counter() - self.t_start
        return self

    @property
    def survival_rate(self) -> float:
        return self.evacuated / self.n_initial if self.n_initial else 0.0

    def run_row(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "map_id": self.map_id,
            "seed": self.seed,
            "config_hash": self.config_hash,
            "code_hash": self.code_hash,
            "maps_hash": self.maps_hash,
            "experiment_hash": self.experiment_hash,
            "n_initial": self.n_initial,
            "evacuated": self.evacuated,
            "dead": self.dead,
            "trapped": self.trapped,
            "survival_rate": self.survival_rate,
            "clearance_turn": self.clearance_turn,
            "mean_evac_turn": self.mean_evac_turn,
            "median_evac_turn": self.median_evac_turn,
            "voluntary_waits": self.voluntary_waits,
            "congestion_waits": self.congestion_waits,
            "replans": self.replans,
            "expanded_nodes": self.expanded_nodes,
            "generated_nodes": self.generated_nodes,
            "search_runtime": self.search_runtime,
            "ga_generations": self.ga_generations,
            "ga_evaluations": self.ga_evaluations,
            "ga_best_fitness": self.ga_best_fitness,
            "total_runtime": self.total_runtime,
            "turns": self.turns,
            "finished_reason": self.finished_reason,
        }

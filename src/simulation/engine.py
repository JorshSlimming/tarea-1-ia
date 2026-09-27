"""SimulationEngine: solo el motor modifica el mundo.

Orden del turno (docs/02_decisiones/fuego.md):
1. snapshot; 2. replanificar; 3. proponer; 4. conflictos; 5. mover;
6. evacuar; 7. propagar (timeline precalculado); 8. muertes; 9. atrapados
(flood-fill desde salida, congestion ignorada); 10. metricas; 11. turno++.
"""

from __future__ import annotations

from collections import deque

from src.domain.enums import Action, AgentStatus, Terrain
from src.domain.models import Agent, Scenario
from src.experiment.metrics import RunMetrics
from src.planners.base import Planner
from .conflicts import resolve
from .state import SimulationState, make_snapshot, rebuild_occupancy


class SimulationEngine:
    def __init__(
        self,
        scenario: Scenario,
        planner: Planner,
        max_turns: int = 200,
        lam: float = 4.0,
        algorithm_name: str = "",
        config_hash: str = "",
        code_hash: str = "",
        maps_hash: str = "",
        experiment_hash: str = "",
        fire_timeline: tuple[frozenset, ...] | None = None,
    ) -> None:
        from src.domain.map import load_map

        self.scenario = scenario
        self.planner = planner
        self.max_turns = max_turns
        self.lam = lam
        self.smap = load_map(f"maps/{scenario.map_id}.txt")
        self.timeline = (
            fire_timeline if fire_timeline is not None else scenario.fire_timeline
        )
        self.metrics = RunMetrics(
            algorithm=algorithm_name or getattr(planner, "name", "?"),
            map_id=scenario.map_id,
            seed=scenario.seed,
            config_hash=config_hash,
            code_hash=code_hash,
            maps_hash=maps_hash,
            experiment_hash=experiment_hash,
        )
        self.is_ga = getattr(planner, "name", "") == "ga"
        self.state = SimulationState(
            smap=self.smap,
            agents=[
                Agent(id=i, position=p) for i, p in enumerate(scenario.spawns)
            ],
        )
        rebuild_occupancy(self.state)

    # -- helpers ------------------------------------------------------
    def _flood_reachable(self) -> set[tuple[int, int]]:
        seen = {self.smap.exit_pos}
        queue = deque([self.smap.exit_pos])
        fire = self.state.fire_cells
        while queue:
            r, c = queue.popleft()
            for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
                nxt = (r + dr, c + dc)
                if (
                    nxt not in seen
                    and self.smap.is_traversable(*nxt)
                    and nxt not in fire
                ):
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def _actives(self) -> list[Agent]:
        return [a for a in self.state.agents if a.status is AgentStatus.ACTIVE]

    # -- main loop ----------------------------------------------------
    def run(self) -> RunMetrics:
        st = self.state
        # Fuego inicial: timeline[0] pudo traer foco sobre celda ocupable.
        st.fire_cells = self.timeline[0] if self.timeline else frozenset()
        self._kill_on_fire(turn=0)
        rebuild_occupancy(st)
        while self._actives() and st.turn < self.max_turns:
            self._step()
        reason = "ALL_RESOLVED" if not self._actives() else "TIMEOUT"
        if reason == "TIMEOUT":
            for a in self._actives():
                a.status = AgentStatus.TRAPPED
                a.status_reason = "TIMEOUT"
            rebuild_occupancy(st)
        return self.metrics.finalize(self.state.agents, st.turn, reason)

    def _step(self) -> None:
        st = self.state
        snap = make_snapshot(st, self.lam)
        intentions: dict[int, Action] = {}
        planned_wait: set[int] = set()
        actives = self._actives()
        positions = {a.id: a.position for a in actives}
        for agent in actives:
            result = self.planner.plan(
                snap, agent.position, self.smap.exit_pos,
                agent_id=agent.id, turn=st.turn,
            )
            agent.replans += 1
            self.metrics.on_plan(result, is_ga=self.is_ga)
            if result.success and result.actions:
                action = result.actions[0]
                intentions[agent.id] = action
                if action is Action.WAIT:
                    planned_wait.add(agent.id)
            else:
                # failure del planner != TRAPPED: WAIT y reintentar.
                intentions[agent.id] = Action.WAIT
                planned_wait.add(agent.id)
        out = resolve(snap, intentions, positions, self.scenario.conflict_seed, st.turn)
        by_id = {a.id: a for a in self.state.agents}
        for aid, dest in out.dest.items():
            by_id[aid].position = dest
        # voluntary = WAIT planificado y quieto; congestion = rechazado.
        for aid, agent in by_id.items():
            if agent.status is not AgentStatus.ACTIVE:
                continue
            if aid in out.congestion_wait:
                agent.congestion_waits += 1
            elif aid in planned_wait and out.dest[aid] == positions[aid]:
                agent.voluntary_waits += 1
        rebuild_occupancy(st)
        # Evacuar: entrar a EXIT (capacidad 1/turno: solo uno por turno).
        # Orden determinista: menor id primero (mismo criterio que conflictos).
        arrivals = [a for a in self._actives() if a.position == self.smap.exit_pos]
        # Solo puede evacuar uno por turno: el resto queda en la salida
        # ocupándola (capacidad 1) hasta el próximo turno.
        for agent in sorted(arrivals, key=lambda a: a.id)[1:]:
            agent.congestion_waits += 1  # salida ocupada este turno
        evacuated_now = (
            sorted(arrivals, key=lambda a: a.id)[:1] if arrivals else []
        )
        for agent in evacuated_now:
            agent.status = AgentStatus.EVACUATED
            agent.status_reason = ""
            # La primera acción ejecutada corresponde al turno 1, no al 0.
            agent.evacuation_turn = st.turn + 1
        rebuild_occupancy(st)
        # Fuego: timeline precalculado (turno t -> t+1).
        if st.turn + 1 < len(self.timeline):
            st.fire_cells = self.timeline[st.turn + 1]
        # El peligro actualizado ocurre al completar el turno t+1.
        self._kill_on_fire(turn=st.turn + 1)
        # Atrapados: activos fuera del componente de la salida.
        reachable = self._flood_reachable()
        for agent in self._actives():
            if agent.position not in reachable:
                agent.status = AgentStatus.TRAPPED
                agent.status_reason = "DISCONNECTED"
        # Mantener la invariante: occupancy contiene sólo agentes ACTIVE.
        rebuild_occupancy(st)
        st.turn += 1

    def _kill_on_fire(self, turn: int) -> None:
        for agent in self._actives():
            if agent.position in self.state.fire_cells:
                agent.status = AgentStatus.DEAD
                agent.status_reason = "FIRE"
                agent.death_turn = turn

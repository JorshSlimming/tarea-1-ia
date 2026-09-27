"""Generación de escenarios (docs/02_decisiones/mapas_y_entorno.md).

Scenario = (map_id, seed): spawns, foco, fire timeline y seeds derivadas.
Una sola generación -> los cinco algoritmos enfrentan lo mismo.
"""

from __future__ import annotations

from src.domain.map import load_map, manhattan, spawn_candidates
from src.domain.models import Scenario, StaticMap
from .fire import precompute_timeline
from .rng import derive_seed, make_rng


def pick_spawns(
    smap: StaticMap,
    num_agents: int,
    seed: int,
    min_manhattan: int = 8,
) -> tuple[tuple[int, int], ...]:
    cands = spawn_candidates(smap, min_manhattan)
    rng = make_rng(seed, "spawn", smap.map_id)
    picks = rng.sample(sorted(cands), num_agents)
    return tuple(picks)


def pick_fire_origin(
    smap: StaticMap,
    spawns: tuple[tuple[int, int], ...],
    seed: int,
    min_exit: int = 6,
    min_agents: int = 4,
) -> tuple[int, int]:
    from src.domain.enums import Terrain

    # Celdas quemables: piso/estrecho, sin agente, lejos de salida y agentes.
    spawn_set = set(spawns)

    valid = [
        (r, c)
        for r in range(smap.rows)
        for c in range(smap.cols)
        if smap.grid[r][c] in (Terrain.FLOOR, Terrain.NARROW)
        and (r, c) not in spawn_set
        and manhattan((r, c), smap.exit_pos) >= min_exit
        and all(manhattan((r, c), s) >= min_agents for s in spawns)
    ]
    if not valid:
        raise ValueError(f"{smap.map_id}/{seed}: sin celda válida para foco de fuego")
    rng = make_rng(seed, "fire_origin", smap.map_id)
    return rng.choice(sorted(valid))


def build_scenario(
    smap: StaticMap,
    seed: int,
    num_agents: int = 30,
    k: int = 3,
    p: float = 0.3,
    max_turns: int = 200,
) -> Scenario:
    spawns = pick_spawns(smap, num_agents, seed)
    origin = pick_fire_origin(smap, spawns, seed)
    fire_rng = make_rng(seed, "fire", smap.map_id)
    timeline = precompute_timeline(smap, origin, k, p, max_turns, fire_rng)
    return Scenario(
        map_id=smap.map_id,
        seed=seed,
        spawns=spawns,
        fire_origin=origin,
        fire_timeline=timeline,
        conflict_seed=derive_seed(seed, "conflicts", smap.map_id),
        ga_seed=derive_seed(seed, "ga"),
    )


def build_scenario_from_file(
    map_path: str,
    seed: int,
    num_agents: int = 30,
    k: int = 3,
    p: float = 0.3,
    max_turns: int = 200,
) -> Scenario:
    return build_scenario(
        load_map(map_path), seed, num_agents=num_agents, k=k, p=p,
        max_turns=max_turns,
    )

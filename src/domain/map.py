"""Carga y validación de mapas (mapas_y_entorno.md, testing.md)."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from .enums import Terrain
from .models import StaticMap

SYMBOL_TO_TERRAIN: dict[str, Terrain] = {
    "#": Terrain.WALL,
    ".": Terrain.FLOOR,
    "n": Terrain.NARROW,
    "E": Terrain.EXIT,
}


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def parse_map(lines: list[str], map_id: str) -> StaticMap:
    rows = [ln.rstrip("\n") for ln in lines if ln.strip() != ""]
    if not rows:
        raise ValueError(f"{map_id}: mapa vacío")
    width = len(rows[0])
    for i, ln in enumerate(rows):
        if len(ln) != width:
            raise ValueError(f"{map_id}: fila {i} longitud {len(ln)} != {width}")
        for ch in ln:
            if ch not in SYMBOL_TO_TERRAIN:
                raise ValueError(f"{map_id}: símbolo inválido {ch!r} en fila {i}")
    grid = tuple(tuple(SYMBOL_TO_TERRAIN[ch] for ch in ln) for ln in rows)
    exits = [
        (r, c)
        for r in range(len(rows))
        for c in range(width)
        if grid[r][c] is Terrain.EXIT
    ]
    if len(exits) == 0:
        raise ValueError(f"{map_id}: sin salida (se exige exactamente una)")
    if len(exits) > 1:
        raise ValueError(f"{map_id}: {len(exits)} salidas (se exige exactamente una)")
    return StaticMap(
        map_id=map_id, rows=len(rows), cols=width, grid=grid, exit_pos=exits[0]
    )


def load_map(path: str | Path, map_id: str | None = None) -> StaticMap:
    p = Path(path)
    return parse_map(p.read_text(encoding="utf-8").splitlines(), map_id or p.stem)


def reachable_from_exit(smap: StaticMap) -> set[tuple[int, int]]:
    """BFS desde la salida sobre celdas no-muro (congestión ignorada: es temporal)."""
    seen = {smap.exit_pos}
    queue = deque([smap.exit_pos])
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            nxt = (r + dr, c + dc)
            if nxt not in seen and smap.is_traversable(*nxt):
                seen.add(nxt)
                queue.append(nxt)
    return seen


def spawn_candidates(
    smap: StaticMap, min_manhattan: int = 8
) -> list[tuple[int, int]]:
    """Celdas válidas de aparición: no muro/salida, Manhattan >= umbral."""
    out = []
    for r in range(smap.rows):
        for c in range(smap.cols):
            t = smap.grid[r][c]
            if t is Terrain.WALL or t is Terrain.EXIT:
                continue
            if manhattan((r, c), smap.exit_pos) >= min_manhattan:
                out.append((r, c))
    return out


def validate_map(
    smap: StaticMap,
    num_agents: int = 30,
    min_spawn_manhattan: int = 8,
    expected_dims: tuple[int, int] | None = (25, 25),
) -> list[str]:
    """Devuelve lista de errores; vacía = mapa válido."""
    errors: list[str] = []
    if expected_dims is not None and (smap.rows, smap.cols) != expected_dims:
        errors.append(
            f"dimensiones {(smap.rows, smap.cols)} != esperadas {expected_dims}"
        )
    cands = spawn_candidates(smap, min_spawn_manhattan)
    if len(cands) < num_agents:
        errors.append(
            f"solo {len(cands)} celdas de spawn (manhattan>={min_spawn_manhattan}), "
            f"se exigen {num_agents}"
        )
    reach = reachable_from_exit(smap)
    unreachable = [c for c in cands if c not in reach]
    if unreachable:
        errors.append(
            f"{len(unreachable)} celdas de spawn sin conexión física a la salida"
        )
    return errors

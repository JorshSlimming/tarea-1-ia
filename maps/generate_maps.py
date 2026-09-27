"""Generador determinista de los 3 layouts 25x25.

Topologias (docs/02_decisiones/mapas_y_entorno.md):
- map1: alta densidad + bandas que convergen a cuellos 'n' escalonados.
- map2: laberinto corporativo / oficinas con muchas puertas.
- map3: semiabierto con pilares y 2 compuertas angostas.

Simbolos: '#' muro, '.' piso C=2, 'n' estrecho C=1, 'E' salida C=1.
"""

from __future__ import annotations

R = C = 25


def new_grid() -> list[list[str]]:
    g = [["."] * C for _ in range(R)]
    for i in range(R):
        g[i][0] = g[i][C - 1] = "#"
    for j in range(C):
        g[0][j] = g[R - 1][j] = "#"
    return g


def hwall(g, r, c0, c1, gaps=None):
    gaps = gaps or {}
    for c in range(c0, c1 + 1):
        g[r][c] = gaps.get(c, "#")


def vwall(g, c, r0, r1, gaps=None):
    gaps = gaps or {}
    for r in range(r0, r1 + 1):
        g[r][c] = gaps.get(r, "#")


def block(g, r0, c0, h, w):
    for r in range(r0, r0 + h):
        for c in range(c0, c0 + w):
            g[r][c] = "#"


def to_rows(g) -> list[str]:
    return ["".join(row) for row in g]


def gen_map1() -> list[str]:
    """Serpentina: 3 muros alternados con pasos de 2 celdas ('n'+'.').
    Conectividad estructural: el unico eje de paso es la serpentina;
    stubs de largo<=3 y bloques 2x2 en pasillos de 5 filas no pueden sellar.
    Carril cols 11-13 en banda D siempre libre (aproximacion a la salida)."""
    g = new_grid()
    # Muros de banda con paso alternado este/oeste/este.
    hwall(g, 6, 1, 23, {21: "n", 22: "."})   # paso este
    hwall(g, 12, 1, 23, {2: ".", 3: "n"})    # paso oeste
    hwall(g, 18, 1, 23, {21: "n", 22: "."})  # paso este
    # Stubs verticales adosados a un muro (fuerzan zigzag, largo<=3).
    vwall(g, 8, 3, 5)        # banda A, adosado a muro fila 6
    vwall(g, 14, 1, 3)       # banda A, adosado a borde superior
    vwall(g, 4, 7, 9)        # banda B, adosado a muro fila 6
    vwall(g, 12, 9, 11)      # banda B, adosado a muro fila 12
    vwall(g, 19, 7, 9)       # banda B, adosado a borde... no: flotante corto
    vwall(g, 7, 13, 15)      # banda C, adosado a muro fila 12
    vwall(g, 15, 15, 17)     # banda C, adosado a muro fila 18
    vwall(g, 5, 19, 21)      # banda D, adosado a muro fila 18
    vwall(g, 16, 21, 23)     # banda D, adosado a borde inferior
    # Bloques 2x2 (nunca sellan pasillos de 5 filas; fuera del carril 11-13 en D).
    block(g, 1, 16, 2, 2)
    block(g, 8, 6, 2, 2)
    block(g, 7, 15, 2, 2)
    block(g, 14, 4, 2, 2)
    block(g, 15, 18, 2, 2)
    block(g, 20, 3, 2, 2)
    block(g, 19, 18, 2, 2)
    g[24][12] = "E"
    return to_rows(g)


def gen_map2() -> list[str]:
    """Oficinas: reticula de salas con 2 puertas por muro (una 'n').
    Menos redundancia que 4 puertas: el fuego puede aislar salas y
    forzar rodeos con costo de congestion."""
    g = new_grid()
    for c in (6, 12, 18):
        vwall(g, c, 1, 23, {9: ".", 16: "n"})
    for r in (6, 12, 18):
        hwall(g, r, 1, 23, {3: ".", 9: ".", 15: ".", 21: "n"})
    # Pilares 2x2 en salas grandes (densidad sin sellar: dejan paso >=3).
    block(g, 2, 2, 2, 2)
    block(g, 8, 14, 2, 2)
    block(g, 14, 8, 2, 2)
    block(g, 20, 14, 2, 2)
    g[10][24] = "E"
    return to_rows(g)


def gen_map3() -> list[str]:
    """Espacio semiabierto: pilares dispersos + compuerta central y lateral."""
    g = new_grid()
    for r0, c0 in [(4, 4), (4, 19), (19, 4), (19, 19),
                   (10, 7), (10, 16), (16, 10), (7, 14)]:
        block(g, r0, c0, 2, 2)
    hwall(g, 12, 9, 15, {12: "n"})  # compuerta central
    vwall(g, 5, 4, 8, {6: "n"})     # compuerta lateral
    g[0][12] = "E"
    return to_rows(g)


GENERATORS = {"map1": gen_map1, "map2": gen_map2, "map3": gen_map3}


def main() -> None:
    import sys
    from pathlib import Path

    from src.domain.map import parse_map, spawn_candidates, validate_map

    outdir = Path("maps")
    outdir.mkdir(exist_ok=True)
    ok = True
    for mid, gen in GENERATORS.items():
        rows = gen()
        sm = parse_map(rows, mid)
        errs = validate_map(sm)
        walls = sum(r.count("#") for r in rows)
        print(
            f"{mid}: exit={sm.exit_pos} walls={walls}/625 ({walls / 6.25:.1f}%) "
            f"spawn={len(spawn_candidates(sm))} errors={errs}"
        )
        if errs:
            ok = False
            continue
        (outdir / f"{mid}.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"  -> escrito maps/{mid}.txt")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

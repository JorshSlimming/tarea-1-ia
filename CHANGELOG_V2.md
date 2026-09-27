# Changelog — revisión V2

Esta versión parte del benchmark completo `final_v1` y corrige problemas detectados al revisar código + resultados. **No se sobrescribe `final_v1`**: se conserva como baseline histórico.

## Correcciones de semántica

1. **Turnos 1-based para eventos posteriores a una acción.**
   - Un agente que evacúa tras su primera acción registra `evacuation_turn=1`.
   - Una muerte causada por el fuego actualizado tras el primer paso registra `death_turn=1`.
   - El fuego inicial puede seguir generando `death_turn=0`.

2. **Invariante de ocupación.**
   - Se reconstruye `occupancy` después de muertes, desconexiones y timeout.
   - `occupancy` contiene únicamente agentes `ACTIVE`.

3. **Población guiada real del GA.**
   - En V1, `GUIDED` y `PURE` elegían del mismo alfabeto uniformemente.
   - En V2, el 60% guiado usa acciones válidas y favorece localmente las que reducen Manhattan; el 20% orientado aplica un sesgo aún mayor. No se inyectan rutas BFS/A*.

4. **Mutación efectiva.**
   - Cuando se dispara una mutación, el nuevo gen es distinto del anterior.

5. **`path_cost` del GA.**
   - Ahora representa sólo el costo de ruta; la función objetivo completa se guarda en `metadata["best_objective"]`.

## Optimización del GA

- `Snapshot` compila una vez por turno grids densos de:
  - transitabilidad;
  - costo de transición;
  - heurística Manhattan.
- `occupancy_at()` ya no crea `dict(self.occupancy)` en cada consulta.
- El fitness usa accesos directos a grids 25×25.
- Se usa `set` para detectar repeticiones.
- No se construye un path para cada individuo; sólo para el ganador final.
- Los élites no se reevaluan.
- Se memoizan cromosomas repetidos durante una planificación.

Microbenchmark de referencia en `map1/seed=0`, 30 planificaciones GA sobre el snapshot inicial:

- V1: ~1.75 s
- V2: ~0.34 s
- mejora observada en ese bloque: **~5.2×**

El speedup del benchmark completo depende de cuántos agentes/turnos permanezcan activos y debe medirse con pilotos V2 antes de estimar el tiempo final.

## Reproducibilidad / persistencia

V2 separa:

- `config_hash`
- `code_hash`
- `maps_hash`
- `experiment_hash = hash(config + código + mapas)`

El runner usa `experiment_hash` para `resume`. Si el `outdir` contiene resultados de otro hash, **aborta** en lugar de mezclar CSVs incompatibles.

`manifest.json` registra además información Git cuando está disponible.

## ETA

La ETA ya no usa un único promedio global. Mantiene estimadores por `(mapa, algoritmo)` y divide el trabajo de CPU restante por el número de workers. Esto es mucho más apropiado cuando GA cuesta órdenes de magnitud más que BFS/Greedy.

## Tests

- Se completó el test de BFS que en V1 no tenía asserts.
- Se eliminó un assert del GA que terminaba en `or True`.
- Se agregaron tests para:
  - inicialización guiada;
  - turnos 1-based;
  - limpieza de ocupación;
  - `path_cost` del GA;
  - rechazo de mezcla de experiment hashes.

Suite V2 al empaquetar: **56 tests passing**.

## No modificado intencionalmente

- Función de congestión.
- Fuego `k=2, p=0.4` del benchmark final.
- 30 agentes.
- Los tres mapas.
- BFS/UCS/Greedy/A* y Manhattan.
- Resolución simultánea de conflictos.
- Early stopping del GA por estancamiento. En V2 queda explícitamente tratado como presupuesto computacional, incluso si aún no existe una ruta completa.

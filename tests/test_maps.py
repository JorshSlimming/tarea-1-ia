"""Tests de mapas (testing.md: símbolos/dims, salidas, capacidad, conectividad)."""

import pytest

from src.domain.enums import Terrain
from src.domain.map import load_map, parse_map, validate_map

MAPS = ["map1", "map2", "map3"]

GOOD_7X7 = [
    "#######",
    "#.....#",
    "#.....#",
    "#.....#",
    "#.....#",
    "#.....#",
    "###E###",
]


def test_parse_ok_7x7():
    sm = parse_map(GOOD_7X7, "test7")
    assert (sm.rows, sm.cols) == (7, 7)
    assert sm.exit_pos == (6, 3)


def test_rejects_bad_symbol():
    bad = [row.replace(".", "x", 1) for row in GOOD_7X7]
    with pytest.raises(ValueError, match="símbolo inválido"):
        parse_map(bad, "bad")


def test_rejects_non_rectangular():
    bad = GOOD_7X7[:2] + ["####"] + GOOD_7X7[3:]
    with pytest.raises(ValueError, match="longitud"):
        parse_map(bad, "bad")


def test_rejects_zero_exits():
    bad = [row.replace("E", "#") for row in GOOD_7X7]
    with pytest.raises(ValueError, match="sin salida"):
        parse_map(bad, "bad")


def test_rejects_two_exits():
    bad = GOOD_7X7[:1] + ["#..E..#"] + GOOD_7X7[2:]
    with pytest.raises(ValueError, match="2 salidas"):
        parse_map(bad, "bad")


def test_capacities():
    assert Terrain.FLOOR.capacity == 2
    assert Terrain.NARROW.capacity == 1
    assert Terrain.EXIT.capacity == 1
    assert Terrain.WALL.capacity == 0


def test_small_map_valid_with_own_params():
    sm = parse_map(GOOD_7X7, "test7")
    assert validate_map(sm, num_agents=5, min_spawn_manhattan=4,
                        expected_dims=(7, 7)) == []


@pytest.mark.parametrize("map_id", MAPS)
def test_final_map_valid(map_id):
    sm = load_map(f"maps/{map_id}.txt")
    assert (sm.rows, sm.cols) == (25, 25)
    assert validate_map(sm) == []

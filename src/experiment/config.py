"""Configuración experimental y huellas de reproducibilidad.

V2 separa cuatro conceptos:
- config_hash: sólo el JSON efectivo;
- code_hash: `main.py` + `src/**/*.py`;
- maps_hash: mapas referenciados por la configuración;
- experiment_hash: combinación de los tres anteriores.

El benchmark usa `experiment_hash` para resume/mezcla de resultados. Así un
cambio de código o mapa no puede continuar silenciosamente un CSV anterior.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_hash(cfg: dict) -> str:
    canonical = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _repo_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root).resolve()
    return Path(__file__).resolve().parents[2]


def _files_hash(paths: list[Path], root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p.relative_to(root))):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        h.update(rel)
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def code_hash(root: str | Path | None = None) -> str:
    base = _repo_root(root)
    paths = [base / "main.py"]
    paths.extend((base / "src").rglob("*.py"))
    existing = [p for p in paths if p.exists()]
    return _files_hash(existing, base)


def maps_hash(cfg: dict, root: str | Path | None = None) -> str:
    base = _repo_root(root)
    paths = [base / "maps" / f"{mid}.txt" for mid in cfg.get("maps", [])]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"mapas faltantes para hash: {missing}")
    return _files_hash(paths, base)


def experiment_hash(cfg: dict, root: str | Path | None = None) -> str:
    payload = {
        "config_hash": config_hash(cfg),
        "code_hash": code_hash(root),
        "maps_hash": maps_hash(cfg, root),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def git_info(root: str | Path | None = None) -> dict[str, str | bool | None]:
    base = _repo_root(root)
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=base, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=base, text=True,
            stderr=subprocess.DEVNULL,
        ).strip())
        return {"git_commit": commit, "git_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "git_dirty": None}


def provenance(cfg: dict, root: str | Path | None = None) -> dict:
    return {
        "config_hash": config_hash(cfg),
        "code_hash": code_hash(root),
        "maps_hash": maps_hash(cfg, root),
        "experiment_hash": experiment_hash(cfg, root),
        **git_info(root),
    }

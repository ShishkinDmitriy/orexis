"""Config loading: .env plus the plants/thresholds YAML."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# backend/ project root (holds config/). .env lives at the repo root, one level up,
# where docker-compose reads it too — so search upward for it.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _find_upwards(name: str, start: Path) -> Path | None:
    for d in (start, *start.parents):
        candidate = d / name
        if candidate.exists():
            return candidate
    return None


_env = _find_upwards(".env", PROJECT_ROOT)
if _env:
    load_dotenv(_env)


def load_plants(path: str | Path | None = None) -> dict:
    """Load config/plants.yaml (plant list + per-species bands)."""
    path = Path(path) if path else PROJECT_ROOT / "config" / "plants.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

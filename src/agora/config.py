"""Config loading: .env plus the plants/thresholds YAML."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def load_plants(path: str | Path | None = None) -> dict:
    """Load config/plants.yaml (plant list + per-species bands)."""
    path = Path(path) if path else ROOT / "config" / "plants.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

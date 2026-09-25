"""Where the worlds are, for the operator's tools — found by looking, never listed.

A world is a directory under `world/` holding the documents it is written in. The tools are handed
a world's name and refuse rather than guess: there is no default world, because a fallback puts a
misconfigured agent on the same topics as the real one. What a world SAYS is read as an agent boots
it (`agent.runtime.world_of`); this module only says where it is.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORLDS_ROOT = REPO_ROOT / "world"
DOCUMENTS = (".ttl", ".trig")


def _documents(world: Path) -> list[Path]:
    return sorted(p for p in world.iterdir() if p.is_file() and p.suffix in DOCUMENTS) if world.is_dir() else []


def worlds() -> list[str]:
    """Every world on disk: a directory under `world/` holding documents."""
    if not WORLDS_ROOT.is_dir():
        return []
    return sorted(d.name for d in WORLDS_ROOT.iterdir() if _documents(d))


def world_dir(name: str) -> Path:
    """One world's directory, or a refusal that names the ones there are."""
    path = WORLDS_ROOT / name
    if not _documents(path):
        raise SystemExit(f"no world called {name!r} in world/ — there is {', '.join(worlds()) or 'nothing'}")
    return path


def env(name: str, default: str | None = None) -> str | None:
    """A deployment fact from the environment, never a belief."""
    return os.environ.get(name, default)

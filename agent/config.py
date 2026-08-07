"""Environment only.

There is no config file: the world (topology) and each agent's beliefs (desire, limits,
cadence, prices) live in the belief base, authored at genesis in `world/<name>/*.ttl`. What is
left here is *deployment* — where the services are and whether this box may open a valve —
which is not a belief anyone holds.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# The repo root. This package sits directly in it, beside the other discovered trees, so the
# root is one level up and there is no project-versus-repo distinction to keep straight — the
# `PROJECT_ROOT.parent` dance every consumer used to do existed only because of a src/ layout.
REPO_ROOT = Path(__file__).resolve().parents[1]


def _find_upwards(name: str, start: Path) -> Path | None:
    for d in (start, *start.parents):
        candidate = d / name
        if candidate.exists():
            return candidate
    return None


def _load_env() -> None:
    """One file, and not at the repo root: `infra/.env` says where the shared series store is.

    That is the whole of the environment now. What a thing IS and what it may DO are in the
    model — a device that must not move water is declared as one, not disarmed by a variable
    that can silently disagree with the world.

    Optional: in a container the value arrives as `env_file`. This is host-run convenience.
    """
    infra = _find_upwards("infra/.env", REPO_ROOT)
    if infra:
        load_dotenv(infra)



_load_env()


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

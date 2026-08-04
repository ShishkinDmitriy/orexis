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

# backend/ project root. .env lives at the repo root, one level up, where docker-compose
# reads it too — so search upward for it.
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


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

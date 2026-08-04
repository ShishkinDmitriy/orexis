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


def _load_env() -> None:
    """Two files, by scope, and neither at the repo root.

    `infra/.env` says where the shared series store is. `world/<name>/.env` says what this
    installation may DO with that world — whether a pump is wired, which subjects are
    simulated. Nothing is global, because nothing here is true of every world at once.

    Both are optional: in a container the values arrive as `env_file` and there is no file to
    find. This is the host-run convenience.
    """
    infra = _find_upwards("infra/.env", PROJECT_ROOT)
    if infra:
        load_dotenv(infra)

    # Resolved from the raw environment, not through env(), because this IS how env() gets
    # populated. The world dir wins when set; a container always sets it.
    world = os.environ.get("AGORA_WORLD_DIR")
    if not world:
        name = os.environ.get("AGORA_WORLD", "society")
        world = PROJECT_ROOT.parent / "world" / name
    candidate = Path(world) / ".env"
    if candidate.exists():
        load_dotenv(candidate)


_load_env()


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

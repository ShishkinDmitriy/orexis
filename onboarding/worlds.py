"""Where the worlds are, for the operator's tools — found by looking, never listed.

A world is a directory under `world/` holding the documents it is written in. The tools are handed
a world's name and refuse rather than guess: there is no default world, because a fallback puts a
misconfigured agent on the same topics as the real one. What a world SAYS is read as an agent boots
it and then in the kinds only onboarding reads (`onboarding.reading.world`); this module only says
where it is.
"""

from __future__ import annotations

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


def shown(path: Path) -> Path:
    """A path as a log line says it: relative to the repo where it is under it, whole otherwise —
    a test's copy of a world is not, and a line about it is still a line."""
    return path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path


def agent_secrets(here: Path, agent_id: str) -> Path:
    """Where one agent's secrets are kept: a directory of its own under the world's `secrets/`, named by the one
    short string the agent goes by, and mounted whole into its container and no other — its credentials, its
    certificate, its carriers' secrets and every document only it is handed, under the world directory `here`
    its caller found. Nothing an agent holds is shared
    with another; what is no agent's — the authority, the broker, the boards — stays in `secrets/` itself
    (knowledge/decisions/an-agent-keeps-its-secrets-in-a-directory-of-its-own.md)."""
    return Path(here) / "secrets" / agent_id


def world_dir(name: str) -> Path:
    """One world's directory, or a refusal that names the ones there are."""
    path = WORLDS_ROOT / name
    if not _documents(path):
        raise SystemExit(f"no world called {name!r} in world/ — there is {', '.join(worlds()) or 'nothing'}")
    return path

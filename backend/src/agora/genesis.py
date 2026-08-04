"""Genesis, as an agent experiences it: ratified files in, a belief base out.

There is no store to seed. A world is `world/<name>/` — Turtle the sovereign ratified — and an
agent builds its own belief base from it at boot. The directory is named for the *result*;
genesis is the process that produced it, and lives in this module and in a conversation.
Nothing is shared, nothing is served, and nothing has to be provisioned before an agent runs.

Two operations, and keeping them apart is the whole point (see knowledge/domain/agent.md
§Lifecycle):

    refresh_public()  every start. The T-Box and the world are not the agent's to keep, so
                      they are replaced from the files each time. An agent that restarts into
                      an amended world simply has it.

    birth()           once, ever. Writes the agent's opening beliefs, and only if it has none.
                      Start must never touch them, or a restart would reset the agent to the
                      sovereign's opinion and a belief would be configuration again.

Capabilities are derived here rather than looked up: each package's `rules.ru` runs against the
agent's own copy of the world. Every agent computes the same answer from the same ratified
files, so a derivation needs no authority to have performed it.

See knowledge/decisions/where-the-belief-base-lives.md, knowledge/domain/world.md.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import loader
from .config import PROJECT_ROOT
from .ontology import ONTOLOGY_GRAPH, WORLD_GRAPH, beliefs_graph
from .store import Store, bindings

log = logging.getLogger("genesis")

REPO_ROOT = PROJECT_ROOT.parent
WORLDS_ROOT = REPO_ROOT / "world"
DEFAULT_WORLD = "society"
BELIEFS_DIR = "beliefs"
SECRETS_DIR = "secrets"
BELIEFS_GLOB = "beliefs/*.ttl"


def agent_id_of(path) -> str:
    """`beliefs/fern.ttl` -> `fern` — the agent those beliefs belong to."""
    return Path(path).stem


def worlds() -> list[str]:
    """Every ratified world on disk. Found by looking, like everything else."""
    if not WORLDS_ROOT.is_dir():
        return []
    return sorted(
        d.name for d in WORLDS_ROOT.iterdir() if d.is_dir() and (d / "world.ttl").exists()
    )


def current_world() -> Path:
    """The one world this process belongs to.

    A container is given exactly one, mounted at a fixed path — so an agent is told only its
    own id and never learns that other worlds exist. Outside a container, name one.
    """
    from . import config

    explicit = config.env("AGORA_WORLD_DIR")
    return Path(explicit) if explicit else world_dir(config.env("AGORA_WORLD", DEFAULT_WORLD))


def secrets_dir(world: Path) -> Path:
    """Where a world keeps its signing keys.

    Per world, because they belong to a *society*: the host that runs its market and the
    clearing authority that co-signs. Two worlds are two societies and should not be able to
    sign for each other. Never committed — see .gitignore.
    """
    return world / SECRETS_DIR


def world_dir(name: str) -> Path:
    """One world, or a refusal that names the ones there are."""
    path = WORLDS_ROOT / name
    if not (path / "world.ttl").exists():
        raise SystemExit(
            f"no world called {name!r} in world/ — there is "
            f"{', '.join(worlds()) or 'nothing'}"
        )
    return path


# --- public knowledge: replaced every start ------------------------------------------------

_CAPABILITIES_Q = f"""
SELECT ?agentId (GROUP_CONCAT(?cap; separator=", ") AS ?caps)
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?agent a ag:Agent ; ag:localId ?agentId ; ag:hasCapability ?c .
  BIND(REPLACE(STR(?c), "^.*#", "") AS ?cap)
}} }} GROUP BY ?agentId ORDER BY ?agentId"""


def refresh_public(st: Store, world: Path) -> None:
    """Load the vocabulary and the world, then derive what the wiring implies.

    Safe to run on every start, and meant to be: it replaces only graphs the agent does not
    own. The derivation is re-run because it is a *function* of the world — materialising it
    into the world graph keeps every reader, and every SHACL shape, able to see an agent's
    capabilities without anyone having to compute them again.
    """
    t_box = "\n".join(p.read_text() for p in loader.ontology_files())
    st.put_graph(ONTOLOGY_GRAPH, t_box)
    st.put_graph(WORLD_GRAPH, (world / "world.ttl").read_text())
    for rule in loader.rule_files():
        st.update(rule.read_text())


def derived(st: Store) -> list[tuple[str, str]]:
    """Who the world says exists, and what it turned out to be able to do."""
    return [(r["agentId"], r["caps"]) for r in bindings(st.query(_CAPABILITIES_Q))]


# --- private knowledge: written once ---------------------------------------------------------

def is_born(st: Store, agent_id: str) -> bool:
    """Whether this agent already has beliefs. Birth happens exactly once."""
    return st.has_graph(beliefs_graph(agent_id))


def birth(st: Store, world: Path, agent_id: str, rebirth: bool = False) -> bool:
    """Write an agent's opening beliefs — only if it has none. True if it was born now.

    `rebirth` is the explicit act of discarding who an agent became and returning it to what
    the sovereign authored. It exists because during development that is genuinely useful, and
    it is a flag rather than a side effect because doing it by accident is the bug this
    separation prevents.
    """
    graph = beliefs_graph(agent_id)
    if st.has_graph(graph) and not rebirth:
        return False
    path = world / BELIEFS_DIR / f"{agent_id}.ttl"
    if not path.exists():
        # An agent the world declares but genesis never gave opening beliefs. Its capabilities
        # will fail their own validation at startup, which is where it should be reported.
        return False
    st.put_graph(graph, path.read_text())
    return True


def open_belief_base(world: Path, agent_id: str, path: str | None = None,
                     rebirth: bool = False) -> Store:
    """An agent's whole boot sequence: open the store, refresh the world, be born if new."""
    st = Store(path)
    refresh_public(st, world)
    if birth(st, world, agent_id, rebirth):
        log.info("%s born — opening beliefs written", agent_id)
    return st

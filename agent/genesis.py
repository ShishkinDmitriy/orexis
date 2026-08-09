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

from . import inference, loader, provenance
from .config import REPO_ROOT
from .ontology import (ONTOLOGY_ENTAILED_GRAPH, ONTOLOGY_GRAPH, WORLD_DERIVED_GRAPH,
                       WORLD_ENTAILED_GRAPH, WORLD_GRAPH, beliefs_graph)
from .store import Store, bindings

# Everything public that is computed rather than read from a file. Emptied before each recompute
# so the answer is the files' and not last boot's — a fact that stops being entailed, or a rule
# that stops firing, must stop being present.
COMPUTED_GRAPHS = (ONTOLOGY_ENTAILED_GRAPH, WORLD_ENTAILED_GRAPH, WORLD_DERIVED_GRAPH)

log = logging.getLogger("genesis")

WORLDS_ROOT = REPO_ROOT / "world"
BELIEFS_DIR = "beliefs"
SECRETS_DIR = "secrets"
BELIEFS_GLOB = "beliefs/*.ttl"


def agent_id_of(path) -> str:
    """`beliefs/fern.ttl` -> `fern` — the agent those beliefs belong to."""
    return Path(path).stem


def world_files(world: Path) -> list[Path]:
    """Every Turtle file the world is written in, in a stable order.

    A world is a DIRECTORY of `.ttl`, not one file. The society is one concern and the stand it
    runs on is another; splitting them lets each be read, reviewed and validated on its own while
    they remain one graph to every query. Nothing lists them — a new file is picked up by being
    there, which is the same rule capabilities are found by.

    `beliefs/` is deliberately not swept up: those are per-agent and private, and an agent is
    mounted only its own. Only the world root is public knowledge.
    """
    return sorted(world.glob("*.ttl"))


# What an AGENT is given, which is less. The sovereign reads the whole world — to validate it,
# to generate a board's config.h, to draw it — but an agent queries none of that.
#
# Nothing in the runtime asks which pin a probe is on. It asks what it acts for, what it may
# poll, which topics reach that sensor and how it is driven, and every one of those is stated in
# the society. Pins, wires, rails, silkscreen markings and part models are the sovereign's
# concern: they decide what CAN be built and what a board must be flashed with, and once it is
# built the agent talks to topics.
#
# So a hardware file is not mounted into an agent's container at all, and the enforcement is
# that ABSENCE rather than a rule the agent is trusted to follow — the same shape as onboarding
# being kept out of the image by the Containerfile not naming it. The invariant is checked
# directly in tests/test_layout.py: an agent's world graph contains no hardware vocabulary,
# which also catches someone putting a pin in world.ttl.
HARDWARE_FILES = ("hardware.ttl",)


def society_files(world: Path) -> list[Path]:
    """The world as an AGENT is given it: everything except the stand it runs on.

    `versions.ttl` IS included, unlike `hardware.ttl`, and the difference is not taste. Hardware
    is withheld because an agent must never learn which pin a probe is on — the absence is the
    enforcement. A version chain is neither secret nor large, and the agent needs the version in
    force to stamp on every observation it records, so withholding it would mean withholding
    something it is required to cite.
    """
    return [p for p in world_files(world) if p.name not in HARDWARE_FILES]


# Where a world records what version it is. Kept OUT of the hash below, and that exclusion is
# the whole reason it is a separate file: a version's fingerprint cannot cover the document that
# states the fingerprint, because writing it would change what it describes.
VERSIONS_FILE = "versions.ttl"


def ratified_files(world: Path) -> list[Path]:
    """Exactly what a version's content hash covers: the world, and the stand it runs on.

    NOT `beliefs/` — those never enter the world graph, and an agent's opening beliefs are its
    own. Were they covered, editing fern's target would bump the version stamped on every other
    agent's observations, for a change none of them can see. `ag:underWorldVersion` would then
    record a number that moves for reasons unrelated to the fact it is recording.

    NOT `versions.ttl` — see above.
    """
    return [p for p in world_files(world) if p.name != VERSIONS_FILE]


def worlds() -> list[str]:
    """Every ratified world on disk. Found by looking, like everything else."""
    if not WORLDS_ROOT.is_dir():
        return []
    return sorted(
        d.name for d in WORLDS_ROOT.iterdir() if d.is_dir() and world_files(d)
    )


def current_world() -> Path:
    """The one world this process belongs to.

    A container is given exactly one, mounted at a fixed path — so an agent is told only its
    own id and never learns that other worlds exist. Outside a container, name one.

    **There is no default, deliberately.** Nothing here is true of every world at once, so a
    process that was not told which world it belongs to has been misconfigured, and the useful
    thing to do is say so. The alternative is worse than it looks: falling back to some world
    puts a misconfigured agent on the same topics as the real one, and two agents ingesting the
    same readings is a failure that has cost real time here twice — it looks like doubled data,
    not like a missing variable.
    """
    from . import config

    explicit = config.env("AGORA_WORLD_DIR")
    if explicit:
        return Path(explicit)
    named = config.env("AGORA_WORLD")
    if not named:
        raise SystemExit(
            "no world: set AGORA_WORLD_DIR (a mounted world) or AGORA_WORLD (a name). "
            "Available: " + (", ".join(worlds()) or "none on disk")
        )
    return world_dir(named)


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
    if not world_files(path):
        raise SystemExit(
            f"no world called {name!r} in world/ — there is "
            f"{', '.join(worlds()) or 'nothing'}"
        )
    return path


# --- public knowledge: replaced every start ------------------------------------------------

_CAPABILITIES_Q = f"""
SELECT ?agentId (GROUP_CONCAT(?cap; separator=", ") AS ?caps)
WHERE {{ 
  ?agent a ag:Agent ; ag:localId ?agentId ; ag:hasCapability ?c .
  BIND(REPLACE(STR(?c), "^.*#", "") AS ?cap)
 }} GROUP BY ?agentId ORDER BY ?agentId"""


def refresh_public(st: Store, world: Path) -> None:
    """Load the vocabulary and the world, then derive what the wiring implies.

    Safe to run on every start, and meant to be: it replaces only graphs the agent does not
    own. The derivation is re-run because it is a *function* of the world — materialising it
    into the world graph keeps every reader, and every SHACL shape, able to see an agent's
    capabilities without anyone having to compute them again.

    The entailments come first, and the order is the point: a derivation rule may then ask what
    a thing IS rather than spelling out a subclass path, because by the time it runs the answer
    is asserted. Both are materialisation, one step apart — what the vocabulary implies, then
    what the wiring implies. See agora/inference.py.

    **Each of the three lands somewhere different**, which is the whole of issue #58: the files
    go to the asserted graphs, the closure to the entailed ones, the rules to the derived one.
    Anything computed is cleared first, because it is a function of the files rather than an
    accumulation — a fact that stopped being entailed must stop being present, and only clearing
    makes that true.

    The world is parsed as **TriG**, so a world file may name its own graphs. Every file today is
    ordinary Turtle and behaves exactly as it did, since a document's default graph goes to
    `to_graph` and Turtle is a syntactic subset of TriG.
    """
    t_box = "\n".join(p.read_text() for p in loader.ontology_files())
    st.put_graph(ONTOLOGY_GRAPH, t_box)
    st.put_graph(WORLD_GRAPH, "\n".join(p.read_text() for p in world_files(world)),
                 dataset=True)
    for graph in COMPUTED_GRAPHS:
        st.clear_graph(graph)
    inference.materialise(st)
    for rule in loader.rule_files():
        st.update(rule.read_text())
    # Last, because it describes the result: which graph holds what, in PROV-O, so the
    # store answers that rather than this file's comments. See agora/provenance.py.
    provenance.describe(st, world)


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

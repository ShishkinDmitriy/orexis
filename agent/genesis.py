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
import re
from pathlib import Path

from . import config, inference, loader, provenance, vocabulary
from .config import REPO_ROOT
from .ontology import (GRAPH_PREFIX, ONTOLOGY_ENTAILED_GRAPH, ONTOLOGY_GRAPH, WORLD_DERIVED_GRAPH,
                       WORLD_ENTAILED_GRAPH, WORLD_GRAPH, beliefs_graph)
from .store import NAMESPACES, Store, bindings

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
    """The world as an AGENT is given it: everything except the stand it runs on."""
    return [p for p in world_files(world) if p.name not in HARDWARE_FILES]


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


# A rule that owns a graph of its own names its CLASS, never the graph. `$into(pkg:SomeGraph)`
# is resolved against the vocabulary here, which is the same discipline `store.public_graphs()`
# follows for reads — a graph IRI is an instance, and rule 1 applies to it as much as it applies
# to `ag:fern_agent`.
#
# Generic on purpose. The kernel learns no package's name: a package declares a graph class, types
# one graph as an instance of it, and its rule writes there. `$derived` remains the default and
# means what it always meant, so no existing rule changed.
_INTO = re.compile(r"\$into\(([^)]+)\)")

_GRAPH_OF_CLASS = "SELECT ?g WHERE {{ ?g a <{cls}> }}"


def _expand(prefixed: str) -> str:
    """`ag:ConstraintGraph` -> its full IRI, using the namespaces every rule already has.

    The same table `store.PREFIXES` is built from, so a rule may name a class exactly as it
    names one in its own WHERE clause and there is no second spelling to keep in step.
    """
    label, _, local = prefixed.strip().partition(":")
    namespace = NAMESPACES.get(label)
    if namespace is None or not local:
        raise RuntimeError(
            f"$into({prefixed}) names no known namespace — a rule may use only the prefixes "
            f"`store.PREFIXES` declares, and a package's own arrives from its ontology.ttl")
    return namespace + local


def graph_of_class(st: Store, class_iri: str) -> str:
    """The one graph the vocabulary types as this class. Refused if there is not exactly one.

    Not defaulted and not resolved by picking the first. Two graphs of one class is a legitimate
    thing to READ — that is the whole reason desire is a class rather than a graph — but a write
    has to land somewhere definite, and choosing for the author would put facts in a graph
    nobody named. Zero is the likelier mistake: a package that declared a class and forgot to
    type an instance would otherwise write into a graph called `None`.
    """
    graphs = sorted({r["g"] for r in bindings(st.query(_GRAPH_OF_CLASS.format(cls=class_iri)))})
    if len(graphs) != 1:
        raise RuntimeError(
            f"<{class_iri}> types {len(graphs)} graphs ({', '.join(graphs) or 'none'}) — a rule "
            f"writing into one needs exactly one. Type an instance of it in the ontology that "
            f"declares the class.")
    return graphs[0]


def write_targets(st: Store) -> tuple[str, ...]:
    """Every graph any rule may write into: the world's derived graph, plus each `$into`.

    Asked of the rules rather than listed, so a package that starts owning a graph is
    automatically excluded from what derivations READ, cleared before each recompute, and
    described in the provenance graph. All three follow from being a write target, and all three
    used to be true of exactly one graph because there was exactly one.
    """
    named = {WORLD_DERIVED_GRAPH}
    for path in loader.rule_files():
        for prefixed in _INTO.findall(path.read_text()):
            named.add(graph_of_class(st, _expand(prefixed)))
    return tuple(sorted(named))


def substitute(rule: str, st: Store) -> str:
    """Fill a derivation rule's placeholders in: `$given`, `$derived` and `$into(…)`.

    A rule says what it concludes; where the facts it reads are kept, and where its conclusions
    go, are not its business. Both used to be typed out — four `USING` lines and an `INSERT
    GRAPH`, per rule, per capability — which made every capability author maintain a copy of a
    list, and a graph IRI is an instance that code was never supposed to name.

    Same idiom as `capabilities/*/review.rq`, whose `$me` and `$evidence` are substituted for
    exactly the same reason: a shipped rule cannot know an instance.

    **`$given` is public MINUS every graph rules write to.** A derivation reads facts, never
    conclusions — otherwise a rule could see what another rule derived and the answer would
    depend on which package happened to load first. Excluding them here rather than trusting each
    rule to leave them out is the difference between an invariant and a convention. It used to be
    one graph and is now however many `write_targets` finds, which is the same invariant asked
    of the rules instead of remembered.

    Comment lines are left alone. They talk *about* the placeholders, and substituting into
    prose spliced a five-line `USING` block into the middle of a sentence — which SPARQL then
    reported as a syntax error twenty lines from anything a reader had written.
    """
    targets = write_targets(st)
    given = "\n".join(f"USING <{g}>" for g in st.public_graphs() if g not in targets)
    out = []
    for line in rule.splitlines():
        if not line.lstrip().startswith("#"):
            line = line.replace("$given", given).replace("$derived", f"<{WORLD_DERIVED_GRAPH}>")
            line = _INTO.sub(
                lambda m: f"<{graph_of_class(st, _expand(m.group(1)))}>", line)
        out.append(line)
    return "\n".join(out)


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
    # The T-Box is in, so a rule's `$into` can be resolved: a write target is discovered from
    # the vocabulary, and everything below treats all of them alike. Computed before the clear
    # rather than after, because a graph cleared is a graph whose class assertion still stands —
    # that lives in the ontology, not in the graph itself.
    targets = write_targets(st)
    for graph in set(COMPUTED_GRAPHS) | set(targets):
        st.clear_graph(graph)
    inference.materialise(st)
    for rule in loader.rule_files():
        st.update(substitute(rule.read_text(), st))
    # Last, because it describes the result: which graph holds what, in PROV-O, so the
    # store answers that rather than this file's comments. See agora/provenance.py.
    provenance.describe(st, world, targets)


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


def endow(st: Store, world: Path, agent_id: str) -> list[str]:
    """Give an already-born agent whatever the sovereign has authored SINCE its birth (#202).

    An amendment may grant a capability whose opening beliefs an existing volume has never
    held — the dealer's buy side arrived exactly so, and the agent crash-looped while the
    only remedy was discarding who it had become. The unit is the (subject, predicate) pair:
    held pairs are the agent's, revisions included, and are never touched; never-held pairs
    arrive with their structures. This is not a reset and not rebirth — rebirth stays the
    explicit act of discarding, and this is the opposite: history kept, grant delivered.
    Returns the endowed terms, so boot can say what changed; empty on every ordinary boot.
    """
    path = world / BELIEFS_DIR / f"{agent_id}.ttl"
    if not path.exists() or not st.has_graph(beliefs_graph(agent_id)):
        return []
    return st.endow_graph(beliefs_graph(agent_id), path.read_text())


def drop_ghost_graphs(st: Store, agent_id: str) -> list[str]:
    """Remove graphs nothing declares and nobody owns — the amendment's litter.

    Public knowledge is exactly what the vocabulary says it is, and a public graph is
    REPLACED on every start by whatever declares it. So a graph that stops being declared is
    never cleared by anyone: it sits in the volume for ever, holding facts in a spelling the
    code no longer speaks, and the first thing that notices is a migration refusing to guess
    what `desire:desires` meant — which is exactly how this was found, on the first live
    migration after the mind's states moved.

    Conservative by construction: a graph is a ghost only if the vocabulary types it as
    nothing AND it is none of this agent's own. Anything owned or declared is left alone,
    because the safe direction to fail is to keep too much.
    """
    from .ontology import AG, PROVENANCE_GRAPH

    declared = {r["g"] for r in bindings(st.query("SELECT ?g WHERE { ?g a ?class }"))
                if r["g"].startswith(GRAPH_PREFIX)}
    # Where per-agent graphs live, ASKED rather than listed: a graph that does not exist
    # until its agent does cannot be declared, so its class states the prefix and this finds
    # the instances under it. Listing them here instead would eat the next package's graphs,
    # which is exactly what the first draft did to review's summaries.
    prefixes = tuple(r["p"] for r in bindings(st.query(
        f"SELECT ?p WHERE {{ ?class <{AG}graphPrefix> ?p }}")))
    ghosts = [g for g in st.graph_names()
              if g.startswith(GRAPH_PREFIX) and g not in declared and g != PROVENANCE_GRAPH
              and not g.startswith(prefixes)]
    for g in ghosts:
        st.clear_graph(g)
    if ghosts:
        log.info("%s: dropped %d graph(s) nothing declares any more: %s",
                 agent_id, len(ghosts), ", ".join(sorted(g.rsplit("/", 2)[-1] for g in ghosts)))
    return ghosts


def classify_own_graphs(st: Store, agent_id: str) -> None:
    """Say what this agent's own graphs ARE, on all three axes (the-mind-is-six-graphs).

    The static graphs declare their own classification in the vocabulary; a per-agent graph
    cannot, because the agent does not exist until it does. So it says so itself, into the
    provenance graph — which already exists to hold statements ABOUT graphs, and is kept out
    of the default graph for exactly that reason: these are mentions, not uses.

    Written on every start rather than once at birth, and cheap: the classification is a
    function of the vocabulary, so a graph whose modality is refined by an amendment says the
    new thing on the next boot without a migration.
    """
    from .ontology import AG, CLASSIFICATION_GRAPH
    from packages.capability.desire.graphs import obligations_graph
    from packages.capability.intention.graphs import intentions_graph

    # Both classes where they differ, because a reader must ASK what a graph is rather than
    # walk a subclass path (one-graph-both-engines-read), and the closure cannot help here:
    # these triples are written at runtime, long after it ran.
    mine = [
        (beliefs_graph(agent_id), ("BeliefsGraph", "DesireGraph"), "Asserted"),
        (intentions_graph(agent_id), ("IntentionGraph",), "Recorded"),
        (obligations_graph(agent_id), ("ConstraintGraph",), "Received"),
    ]
    triples = " ".join(
        f"<{iri}> a {' , '.join(f'<{AG}{c}>' for c in classes)} ; "
        f"<{AG}arrivedBy> <{AG}{arrival}> ."
        for iri, classes, arrival in mine)
    st.clear_graph(CLASSIFICATION_GRAPH)
    st.update(f"INSERT DATA {{ GRAPH <{CLASSIFICATION_GRAPH}> {{ {triples} }} }}")


def open_belief_base(world: Path, agent_id: str, path: str | None = None,
                     rebirth: bool = False) -> Store:
    """An agent's whole boot sequence: open the store, refresh the world, be born if new.

    Then check that the store still speaks this vocabulary. A volume outlives the code that
    wrote it — that is what makes beliefs the agent's rather than the sovereign's — so it can be
    older than the terms the code now asks for, and reading it would find nothing rather than
    fail. Last, because it is about what is in the store once everything that writes has run.
    See agora/vocabulary.py and issue #87.
    """
    st = Store(path)
    refresh_public(st, world)
    born = birth(st, world, agent_id, rebirth)
    if born:
        log.info("%s born — opening beliefs written", agent_id)
    classify_own_graphs(st, agent_id)
    # Before the vocabulary check, deliberately: a ghost graph holds terms this code no
    # longer speaks, and refusing to boot over facts nobody declares any more would be
    # refusing over litter.
    drop_ghost_graphs(st, agent_id)
    vocabulary.check(st, migrating=bool(config.env("AGORA_MIGRATE_BELIEFS")))
    # Endowment comes AFTER the vocabulary check, deliberately: an aged volume's old
    # spellings would read as never-held pairs, and endowing before migrating re-authored a
    # belief the migration was about to convert — the same value twice, found by the
    # migration test the day endowment was born. Migration first puts the volume in today's
    # spelling; whatever is still never-held after that is genuinely a grant.
    if not born and (endowed := endow(st, world, agent_id)):
        log.info("%s endowed — an amendment authored terms this volume never held: %s",
                 agent_id, ", ".join(t.rsplit("#", 1)[-1] for t in endowed))
    return st

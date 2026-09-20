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

import shutil

import logging
import re
from pathlib import Path

from agent import config, inference, provenance, vocabulary

from assembly import loader
from .config import REPO_ROOT
from orexis_agent_progression.ontology import (DESIRE_ASSERTED_GRAPH, ACTIONS_GRAPH, CATALOGUE_GRAPH, GRAPH_PREFIX, OREXIS, roots_graph, ONTOLOGY_ENTAILED_GRAPH, ONTOLOGY_GRAPH, STATE_GRAPH,
                       WORLD_DERIVED_GRAPH,
                       WORLD_ENTAILED_GRAPH, WORLD_GRAPH, picks_graph)
from orexis_agent_deliberation.ontology import DERIVATIONS_GRAPH
from orexis_agent_progression.store import NAMESPACES, Raw, Store, bind, bindings
from orexis_agent_progression.ontology import PUBLIC

# Everything public that is computed rather than read from a file. Emptied before each recompute
# so the answer is the files' and not last boot's — a fact that stops being entailed, or a rule
# that stops firing, must stop being present.
COMPUTED_GRAPHS = (ONTOLOGY_ENTAILED_GRAPH, WORLD_ENTAILED_GRAPH, WORLD_DERIVED_GRAPH,
                   DERIVATIONS_GRAPH)

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

    explicit = config.env("OREXIS_WORLD_DIR")
    if explicit:
        return Path(explicit)
    named = config.env("OREXIS_WORLD")
    if not named:
        raise SystemExit(
            "no world: set OREXIS_WORLD_DIR (a mounted world) or OREXIS_WORLD (a name). "
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
  ?agent a orexis:Agent ; orexis:localId ?agentId ; orexis:hasCapability ?c .
  BIND(REPLACE(STR(?c), "^.*#", "") AS ?cap)
 }} GROUP BY ?agentId ORDER BY ?agentId"""


# A rule that owns a graph of its own names its CLASS, never the graph. `$into(pkg:SomeGraph)`
# is resolved against the vocabulary here, which is the same discipline `store.graphs_of(PUBLIC)`
# follows for reads — a graph IRI is an instance, and rule 1 applies to it as much as it applies
# to `orexis:fern_agent`.
#
# Generic on purpose. The kernel learns no package's name: a package declares a graph class, types
# one graph as an instance of it, and its rule writes there. `$derived` remains the default and
# means what it always meant, so no existing rule changed.
_INTO = re.compile(r"\$into\(([^)]+)\)")



def _expand(prefixed: str) -> str:
    """`orexis:ConstraintGraph` -> its full IRI, using the namespaces every rule already has.

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
    graphs = sorted(st.graphs_of(class_iri, at=None))
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
    given = "\n".join(f"USING <{g}>" for g in st.graphs_of(PUBLIC) if g not in targets)
    out = []
    for line in rule.splitlines():
        if not line.lstrip().startswith("#"):
            line = _INTO.sub(
                lambda m: f"<{graph_of_class(st, _expand(m.group(1)))}>", line)
            line = bind(line, given=Raw(given), derived=WORLD_DERIVED_GRAPH)
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
    what the wiring implies. See orexis/inference.py.

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
    #  The ACTIONS, from the packages that own the acting (#238, an-action-is-one-node): per
    #  way of acting one node — precondition, effect, taker. Beside the T-Box and not inside
    #  it: both are schemas the files assert, but an action carries executable text a planner
    #  runs, and keeping it in a graph of its own means a package that grows one is visible as
    #  a graph that grew rather than as vocabulary that moved.
    st.put_graph(ACTIONS_GRAPH, "\n".join(p.read_text() for p in loader.action_files()))
    #  The asserted-desire graph is REPLACED FROM THE FILES like everything ratified — and
    #  cleared here first, because `put_graph` can only replace graphs the new document still
    #  NAMES: a world that deletes its desire.ttl names nothing, and the dropped want would
    #  survive its own ratification. Named by the kernel as the bootstrap-root exception.
    st.clear_graph(DESIRE_ASSERTED_GRAPH)
    st.put_graph(WORLD_GRAPH, "\n".join(p.read_text() for p in world_files(world)),
                 dataset=True)
    catalogue_public(st)
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
    describe_derivations(st)
    # Last, because it describes the result: which graph holds what, in PROV-O, so the
    # store answers that rather than this file's comments. See orexis/provenance.py.
    provenance.describe(st, world, targets)


def ensure_catalogue(st: Store) -> str:
    """The catalogue, created where the store has none — the one place its name is written:
    it says of itself what it is, and every reader finds it by that
    (one-catalogue-describes-every-graph-and-itself). Genesis is the one writer that creates
    it, at refresh, at birth and at every start, so a bare store may be born into."""
    if st.catalogue is None:
        st.update(f"""INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{
  <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph ; orexis:arrivedBy orexis:Derived . }} }}""")
    return st.catalogue


def describe_derivations(st: Store) -> None:
    """Put what the loaded derivations READ and WRITE into the store, one row per INSERT.

    THE PARTITION IS A FUNCTION OF THE STORE, and this is the half that was not in it. Scopes
    join predicates wherever one action or one derivation touches both (scope-actions); the
    actions have always been in the store, as `orexis:Action` rows a package's `actions.ttl`
    ratifies, while the derivations were rule texts on disk that `scope_actions` read through
    the loader. So the edges the texts make are computed once here, where the rules are already
    being read and run, and `scope_actions` is handed the engine and asks.

    PUBLIC, because the loaded rule set is the same for everyone reading this store, exactly as
    the actions are; computed, so the graph is cleared with the rest of `COMPUTED_GRAPHS` on
    every refresh and never accumulates. Each row is named for the rule file it came from and
    its place in it, so the same rules write the same text — and the name is a file IRI, which
    is this module's to build and not a layer's: `relevance` says what an update's edges ARE
    and would have had to import the container to say where one came from.
    """
    from orexis_agent_deliberation import relevance
    from orexis_agent_deliberation.ontology import ANYTHING, DERIVATION, READS, WRITES

    lines = []
    for path in sorted(loader.rule_files()):
        for n, (reads, writes) in enumerate(relevance.edges_of_update(path.read_text()), 1):
            said = "".join(
                f" ;\n      <{term}> " + (f"<{ANYTHING}>" if side is relevance.ANYTHING
                                          else " , ".join(f"<{p}>" for p in sorted(map(str, side))))
                for term, side in ((READS, reads), (WRITES, writes)) if side is relevance.ANYTHING or side)
            lines.append(f"  <{provenance.file_iri(path)}#{n}> a <{DERIVATION}>{said} .")
    st.update(f"INSERT DATA {{ GRAPH <{DERIVATIONS_GRAPH}> {{\n{chr(10).join(lines)}\n}} }}")


def catalogue_public(st: Store) -> None:
    """Say what the public graphs are, in the catalogue.

    The vocabulary DECLARES its graph instances (`<…/graph/world> a orexis:WorldGraph`, and a
    package's own beside its terms), and that declaration is transcribed here on every start:
    the catalogue is where a reader asks, the T-Box is where a package says. What the catalogue
    said of a public graph before is dropped first, since the vocabulary may have changed its
    mind. A graph instance is known by `orexis:arrivedBy`, which the vocabulary states of a
    graph and of nothing else — no walk of the class hierarchy, which the closure owns."""
    catalogue = ensure_catalogue(st)
    for graph in st.graphs_of(PUBLIC):
        st.update(f"DELETE WHERE {{ GRAPH <{catalogue}> {{ <{graph}> ?p ?o }} }}")
    #  THROUGH `classify`, one row per declaration, so every kind the vocabulary puts the class
    #  beneath stands on the row too — `a orexis:PublicGraph` of a world graph outright — and a
    #  text joining the catalogue asks by any kind without a path. The closure this reads is
    #  the T-Box's `rdfs:subClassOf`, in the store by now; the entailed graph is not, being
    #  materialised later in the same refresh.
    for row in bindings(st.query(
            "SELECT ?g ?class ?arrival WHERE { ?g a ?class ; orexis:arrivedBy ?arrival }",
            [ONTOLOGY_GRAPH])):
        st.classify(row["g"], row["class"], row["arrival"])
    #  The vocabulary graph's own row lands somewhere in that loop, and a row classified before
    #  it had no hierarchy to close over: said again of every row, now that it is there.
    st.close_catalogue()


def _gather_into_catalogue(st: Store) -> None:
    """A volume written when what a graph is, when it holds and how it was loaded lived in
    three graphs of their own — the classification, the periods, the provenance — is gathered
    into the catalogue once, before anything reads it. The old spellings live here and nowhere
    else, since a migration names what it migrates from; the provenance is not carried, being
    rewritten on every start by `provenance.describe`."""
    catalogue = ensure_catalogue(st)
    old = {kind: GRAPH_PREFIX + kind for kind in ("classification", "periods", "provenance")}
    moved = []
    for kind in ("classification", "periods"):
        if st.has_graph(old[kind]):
            st.update(f"ADD <{old[kind]}> TO <{catalogue}>")
            st.clear_graph(old[kind])
            moved.append(kind)
    if st.has_graph(old["provenance"]):
        st.clear_graph(old["provenance"])
    if moved:
        for name in old.values():
            st.update(f"DELETE WHERE {{ GRAPH <{catalogue}> {{ <{name}> ?p ?o }} }}")
        log.info("gathered %s into the catalogue", " and ".join(moved))


def derived(st: Store) -> list[tuple[str, str]]:
    """Who the world says exists, and what it turned out to be able to do."""
    return [(r["agentId"], r["caps"]) for r in bindings(st.query(_CAPABILITIES_Q, st.graphs_of(PUBLIC)))]


# --- private knowledge: written once ---------------------------------------------------------

def is_born(st: Store, agent_id: str) -> bool:
    """Whether this agent already has beliefs. Birth happens exactly once."""
    return st.has_graph(picks_graph(agent_id))


def birth(st: Store, world: Path, agent_id: str, rebirth: bool = False) -> bool:
    """Write an agent's opening beliefs — only if it has none. True if it was born now.

    `rebirth` is the explicit act of discarding who an agent became and returning it to what
    the sovereign authored. It exists because during development that is genuinely useful, and
    it is a flag rather than a side effect because doing it by accident is the bug this
    separation prevents.
    """
    graph = picks_graph(agent_id)
    if st.has_graph(graph) and not rebirth:
        return False
    path = world / BELIEFS_DIR / f"{agent_id}.ttl"
    if not path.exists():
        # An agent the world declares but genesis never gave opening beliefs. Its capabilities
        # will fail their own validation at startup, which is where it should be reported.
        return False
    st.put_graph(graph, path.read_text())
    ensure_catalogue(st)
    st.classify(graph, OREXIS + "PickRecordGraph", OREXIS + "Asserted", agent_uri(st, agent_id))
    author_roots(st, agent_id)
    return True


def _roots_from_the_world(st: Store, agent_id: str) -> Store:
    """What the packages' desire rules make of the world and this agent's record, in a scratch
    store: the ROOTS — every Always desire with its met-tests — in a graph named as the volume's
    roots graph is, so the scratch reads as the volume would. The premises are public knowledge
    and the agent's own record; `$derived` is the roots graph, `$given` the premises, `$me` the
    agent — the substitution the desire modality performed on every rebuild until #644."""
    from assembly import loader

    rows = st.query(f'SELECT ?a WHERE {{ ?a a orexis:Agent ; orexis:localId "{agent_id}" }} LIMIT 1', st.graphs_of(PUBLIC))
    found = rows.get("results", {}).get("bindings", [])
    scratch = Store()
    if not found:
        return scratch
    me = found[0]["a"]["value"]
    premises = list(st.graphs_of(PUBLIC)) + [picks_graph(agent_id)]
    for iri in premises:
        for quad in st.quads(iri):
            scratch._store.add(quad)
    given = "\n".join(f"USING <{g}>" for g in premises)
    for rule in loader.desires_rule_files():
        out = []
        for line in rule.read_text().splitlines():
            if not line.lstrip().startswith("#"):
                line = bind(line, derived=roots_graph(agent_id), given=Raw(given), me=me)
            out.append(line)
        scratch.update("\n".join(out))
    return scratch


def _held_in(store: Store, graph: str) -> list[str]:
    rows = store.query(f"SELECT DISTINCT ?r WHERE {{ GRAPH <{graph}> {{ ?me orexis:holds ?r }} }}", store.graphs_of(PUBLIC))
    return sorted(r["r"]["value"] for r in rows.get("results", {}).get("bindings", []))


def _subgraph_of(scratch: Store, graph: str, top: str) -> list:
    """Every quad reachable from `top` inside `graph`, following objects that are subjects there
    — a root and its met-test shapes, blank nodes and all — plus the triple that holds it.
    NEVER THROUGH THE HOLDER: every met-test shape targets the agent's own node, and the agent
    holds every root, so a walk that crossed it would copy the whole graph twice."""
    HOLDS = "http://example.org/orexis#holds"
    quads = list(scratch.quads(graph))
    by_subject: dict[str, list] = {}
    for q in quads:
        by_subject.setdefault(str(q.subject), []).append(q)
    holders = {str(q.subject) for q in quads if q.predicate.value == HOLDS}
    out, seen, frontier = [], set(holders), [f"<{top}>"]
    while frontier:
        node = frontier.pop()
        if node in seen:
            continue
        seen.add(node)
        for q in by_subject.get(node, ()):
            out.append(q)
            obj = str(q.object)
            if (obj.startswith("<") or obj.startswith("_:")) and obj not in seen:
                frontier.append(obj)
    out.extend(q for q in quads if q.predicate.value == HOLDS and str(q.object) == f"<{top}>")
    return out


def author_roots(st: Store, agent_id: str) -> list[str]:
    """Write the agent's ROOT desires into its roots graph — at birth, all of them; at a later
    boot, only the ones it has never held (#644, a-root-holds-always-and-an-outdated-graph-is-dropped).

    A root is a declaration for the agent's whole life, authored once from the ranges and the
    wiring the world states and holding at every instant, as the T-Box does: the desire
    modality projects this graph and never rebuilds it. An amendment ENDOWS — a never-held root
    arrives with its met-tests, a held one stays whatever the world now says, and removal is a
    rebirth (the record's seam). Returns the roots newly held, so boot can say what changed.
    """
    graph = roots_graph(agent_id)
    scratch = _roots_from_the_world(st, agent_id)
    fresh = _held_in(scratch, graph)
    already = set(_held_in(st, graph)) if st.has_graph(graph) else set()
    new = [r for r in fresh if r not in already]
    for top in new:
        triples = "\n".join(f"{q.subject} {q.predicate} {q.object} ." for q in _subgraph_of(scratch, graph, top))
        if triples:
            st.update(f"INSERT DATA {{ GRAPH <{graph}> {{\n{triples}\n}} }}")
    ensure_catalogue(st)
    st.classify(graph, OREXIS + "DesireGraph", OREXIS + "Asserted", agent_uri(st, agent_id))
    return new


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
    if not path.exists() or not st.has_graph(picks_graph(agent_id)):
        return []
    return st.endow_graph(picks_graph(agent_id), path.read_text())


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
    from orexis_agent_progression.ontology import OREXIS

    #  A GRAPH IS THE AGENT'S BY THE CATALOGUE and by nothing about its name: whatever the
    #  catalogue describes — public, the agent's own, a prediction, a working graph — and the
    #  catalogue itself are kept; a graph under the kernel's prefix the catalogue says nothing
    #  of is the ghost. Run after every owner has spoken (`runtime.Agent`), never before.
    described = set(st.graphs_of(OREXIS + "Graph", at=None)) | {st.catalogue}
    ghosts = [g for g in st.graph_names() if g.startswith(GRAPH_PREFIX) and g not in described]
    for g in ghosts:
        st.clear_graph(g)
    if ghosts:
        log.info("%s: dropped %d graph(s) nothing declares any more: %s",
                 agent_id, len(ghosts), ", ".join(sorted(g.rsplit("/", 2)[-1] for g in ghosts)))
    return ghosts


def agent_uri(st: Store, agent_id: str) -> str | None:
    """The agent the world declares under this id, or None where the world names none — the
    one construction from the id a process is handed that a reader may make."""
    rows = bindings(st.query(f'SELECT ?a WHERE {{ ?a a orexis:Agent ; orexis:localId "{agent_id}" }} LIMIT 1', st.graphs_of(PUBLIC)))
    return rows[0]["a"] if rows else None


def classify_kernel_graphs(st: Store, agent_id: str) -> None:
    """Say what the two graphs the KERNEL writes for an agent are — its pick record and its
    roots — at every start, so a volume written before owners classified their own graphs
    says so too. An owner classifies what it writes (`Store.classify`): the ledger its
    record, the keeper its promises, review its three, the derivation each want, sensing each
    prediction — each at construction or at the write, by the class it declares, whatever
    the graph is called. Boot used to type every per-agent graph by matching names against
    a prefix each class declared (`orexis:graphPrefix`), and was the one reader that
    depended on a name; a name is for eyes now, and code asks the class.
    """
    me = agent_uri(st, agent_id)
    ensure_catalogue(st)
    st.classify(picks_graph(agent_id), OREXIS + "PickRecordGraph", OREXIS + "Asserted", me)
    st.classify(roots_graph(agent_id), OREXIS + "DesireGraph", OREXIS + "Asserted", me)


def _belief_room(path: str | None) -> str | None:
    """Where the belief base lives inside the agent's volume: its own room.

    The volume used to BE the store — one RocksDB directory at the root — and the mind's
    other stores need rooms beside it (a-store-is-a-modality), so the layout is now
    `<state>/belief-base` and siblings. A pre-split volume is recognised by the store's own
    files sitting at the root and moved whole into the room, once; the move is a rename, so
    nothing is copied and an interrupted first boot re-runs it harmlessly.
    """
    if path is None:
        return None
    root = Path(path)
    room = root / "belief-base"
    if (root / "CURRENT").exists() and not room.exists():
        room.mkdir()
        for entry in list(root.iterdir()):
            if entry.name != "belief-base":
                shutil.move(str(entry), str(room / entry.name))
        log.info("belief base moved into its room — the volume grew a mind layout")
    else:
        # A fresh volume: the store only creates its own directory, never the parents —
        # and a caller may hand a path whose parents do not exist yet, as the old layout
        # allowed by pointing the store at the leaf itself.
        room.mkdir(parents=True, exist_ok=True)
    return str(room)


def _move_pick_record(st: Store, agent_id: str) -> None:
    """A volume written when the pick record was called `beliefs/<agent>` is moved to
    `picks/<agent>` once, BEFORE birth asks whether the agent exists: birth reads the record's
    presence as the answer, and the old name left standing would have re-authored every pick
    on the next start — the reset AGENTS.md calls a bug. The old spelling lives here and
    nowhere else, since a migration names what it migrates from; what the classification
    said about the old name follows it, and `classify_kernel_graphs` says the rest."""
    old, new = GRAPH_PREFIX + "beliefs/" + agent_id, picks_graph(agent_id)
    if st.has_graph(new) or not st.has_graph(old):
        return
    st.update(f"MOVE GRAPH <{old}> TO <{new}>")
    st.update(f"""DELETE {{ GRAPH <{st.catalogue}> {{ <{old}> ?p ?o }} }}
INSERT {{ GRAPH <{st.catalogue}> {{ <{new}> ?p ?o }} }}
WHERE  {{ GRAPH <{st.catalogue}> {{ <{old}> ?p ?o }} }}""")
    log.info("%s: pick record moved from %s to %s", agent_id, old, new)


def open_belief_base(world: Path, agent_id: str, path: str | None = None,
                     rebirth: bool = False) -> Store:
    """An agent's whole boot sequence: open the store, refresh the world, be born if new.

    Then check that the store still speaks this vocabulary. A volume outlives the code that
    wrote it — that is what makes beliefs the agent's rather than the sovereign's — so it can be
    older than the terms the code now asks for, and reading it would find nothing rather than
    fail. Last, because it is about what is in the store once everything that writes has run.
    See orexis/vocabulary.py and issue #87.
    """
    st = Store(_belief_room(path))
    refresh_public(st, world)
    _gather_into_catalogue(st)
    st.close_catalogue()              # every row says every kind it is, however it was written
    _move_pick_record(st, agent_id)
    born = birth(st, world, agent_id, rebirth)
    if born:
        log.info("%s born — opening beliefs written", agent_id)
    #  What the readings on record ARE, by the bands this boot's vocabulary declares (#576):
    #  a volume older than the classes holds readings nobody classified, and the next
    #  reading would classify only itself.
    st.entail(STATE_GRAPH)
    classify_kernel_graphs(st, agent_id)
    # Before the vocabulary check, deliberately: a ghost graph holds terms this code no
    # longer speaks, and refusing to boot over facts nobody declares any more would be
    # refusing over litter.
    vocabulary.check(st, migrating=bool(config.env("OREXIS_MIGRATE_BELIEFS")))
    # Endowment comes AFTER the vocabulary check, deliberately: an aged volume's old
    # spellings would read as never-held pairs, and endowing before migrating re-authored a
    # belief the migration was about to convert — the same value twice, found by the
    # migration test the day endowment was born. Migration first puts the volume in today's
    # spelling; whatever is still never-held after that is genuinely a grant.
    if not born and (endowed := endow(st, world, agent_id)):
        log.info("%s endowed — an amendment authored terms this volume never held: %s",
                 agent_id, ", ".join(t.rsplit("#", 1)[-1] for t in endowed))
    if not born and (rooted := author_roots(st, agent_id)):
        log.info("%s endowed — an amendment authored roots this volume never held: %s",
                 agent_id, ", ".join(r.rsplit("#", 1)[-1] for r in rooted))
    return st

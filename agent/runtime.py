"""The runtime of Agent 0.2.0: one process, one agent, one world — booted from the world's files
and run, pass by pass, until nothing is left to pursue.

**A WORLD IS A DIRECTORY OF DOCUMENTS, AND EACH SAYS WHAT IT IS.** `boot` reads the kernel's
T-Box (`agent/ontology.ttl`), the documents of the packages it loads, and every `.ttl` and `.trig`
file in the world's directory, whatever it is called. A Turtle file is
one graph named by its own IRI, and `<> a planning:DesireGraph` in it says what that graph is; a
TriG file names its graphs and states their kinds in its default graph. `store.document` reads
either, and `store.put_document` puts the graphs in and moves the rows about them into the
catalogue, where every reader asks; a document stating no kind, or claiming to be the
catalogue, is refused. The vocabulary goes first, since what a graph is depends on it: every
document that says it is an `orexis:OntologyGraph`, then the closure over `rdfs:subClassOf`,
written into a graph of its own and derived, so that a kind is every kind it is beneath. **A
GRAPH OF A KIND THE VOCABULARY DOES NOT DECLARE IS PASSED OVER**: the kind says who reads a
document, and a world's hardware and where its broker listens are onboarding's to read and not
the agent's (#820, #823). Then the world's public graphs, then who the agent is — off the
society graph, or the world graph of a world with no society, by the one identifier the
process is told — and THE SELF, the agent's self graph put in; then the world's other private
graphs that say they are this agent's, owned by it. The catalogue is closed and the Planner's
`scope` writes the scopes.

**WHOSE A GRAPH IS, IS READ OFF WHAT IT SAYS.** Every graph of the world of a kind that is not
public is some agent's own, and says whose: `<> orexis:beliefsOf :rose_grower` beside its kind,
or, for a self graph, the self it states (`store.whose`). The boot reads every document of the
world — beside it, under `secrets/` and under `beliefs/` — and keeps as its own exactly those
graphs whose content names the agent it was told to be; another agent's are passed over, never
refused, since a world read from a checkout holds every agent's and a container is mounted only
its own, and which files are present is not for the boot to rely on. A graph of an agent's own
naming no agent of the world, or none at all, is refused, as a public graph naming an owner is.

**THE SELF IS AUTHORED, AND THE BOOT CHECKS IT (knowledge/domain/kernel/self.md).** Every text
about the agent asks `?me a orexis:Self` and is bound nothing, so the boot is where the self is
held to one instance: the agent's own documents state exactly one self graph or it does not boot,
and a store's selves, counted in every graph, are that agent alone — a volume whose self is
another agent is the right id handed the wrong volume, and two selves would answer every text for
both without a word. The loader keeps the self to its one home, and refuses it from a peer.

**A PACKAGE IS LOADED ONLY FOR A ROLE THE AGENT IS DECLARED IN
(a-package-is-loaded-only-for-a-role-the-agent-is-declared-in).** The self graph states the
agent's roles beside its self — `:supplier a orexis:Self , market:Host` — and each package declares
the roles it serves in its own `ontology.ttl`, beneath `orexis:Role`; a domain declares roles in its
own words beneath the packages'. So the boot reads the kernel and the world first, finds who the
agent is and puts its self graph in, closes its roles over `rdfs:subClassOf` — the steps the
world's domains state, and the steps each package's ontology states, READ APART so that no
unloaded package's documents enter the store — and only then reads the documents of each package
whose ontology declares a role in that closure: the directory it was read from, found by looking
and never listed. It closes the vocabulary again and takes a second look at any graph of the
world passed over for a kind only such a package declares. There is no default set and no fixed
mind: an agent declaring no role loads nothing, said in the log, and `orexis-onboard` refuses it.
A TRANSPORT IS NO ROLE: it is loaded where a loaded role needs bytes and the society wires a bus
(`TRANSPORTS`) — the one derivation left, since which bus reaches a device is wiring. History and
metrics are deployment's, read from the environment. Hanoi's mover is a planner and an executor,
and loads planning and execution and nothing else — no belief, since its world ships no rules.

**A VOLUME LIVED IN** — a store that already holds a catalogue — forgets every graph a document
put in and nobody owns, and the closure, and reads the documents again: the kernel's, the
packages' and the world's public ones are asserted and replaced at every boot, which is how an
updated ontology reaches a running agent, and the roles are read again, so a package a role
stops calling for stops loading. The agent's own are left as they are, because they are its
beliefs from the first boot on (an-amendment-endows-what-it-grants) — the self graph among them, so
a role declared after birth reaches only a fresh volume, which is a seam the record leaves open.

**A PASS DRAINS, AND THE RUN ENDS WHEN NOBODY HOLDS THE AGENT.** A pass runs every job queued and
what its writes set off, then what is due — planning's pass, execution's walk, a transport's poll,
sensing's ask — each a job a package asked for when it started. A listening transport holds the
agent, and planning holds it while a desire is held or a want stands; planning lets go `met` when
every want is reached and none is walked, and `unreachable` when some stand that nothing this agent
holds reaches — so Hanoi's mover solves its tower and exits. Nothing here is threaded: a pass that
moved nothing sleeps the poll before the next, unless a package asked to go again.

**A PACKAGE HAS A PART, CREATED, LINKED AND STARTED (a-package-starts-itself,
planning-and-execution-meet-at-the-store).** Every package the agent loads that has a `create`
module makes its part, in the order a pass runs them (`PASS`); the parts link, each connecting the signals it owns
to what lies beneath it — the Planner's `plan_published` to the executor, the executor's `commanded`
to the transports and `said` to speech, the deliberator's `revised` heard by the executor; then each
starts, by jobs it `submit`s, timers it asks for (`every`) and graphs written it hears (`on`). The
runtime runs every job and handler on this one thread and knows no package's words.

**WHAT HAPPENED AND HOW THE AGENT IS DOING ARE HEARD, NOT HANDED.** `main` loads a series sink for
every purpose the environment names a store for (`agent/series.py`), and where one is loaded the
runtime creates the part that writes it, as it creates any package's: `agent/history/`, which
writes every event that answers a point — sensing's observation, execution's step taken and how it
ended, each shaped by the package that decides it — and `agent/metrics/`, which tallies every event
whose class says it is reported and writes the window once a minute of real time. Both link to every
part and to the runtime, and neither knows a package's word; the runtime's own events are below: a
graph written, and a pass — its parts in real seconds, the store's size and the process's uptime.
The last window is written as the metrics part stops.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import importlib.util
import logging
import queue
import signal
import sys
import time
from datetime import timedelta
from functools import cache
from pathlib import Path
from urllib.parse import unquote, urlparse

import pyoxigraph as ox

from agent import clock
from agent import series
from agent.lifecycle import MET, UNFINISHED, UNREACHABLE, Signal  # noqa: F401 — the outcomes, re-exported
from agent.metrics import Laps, Level, Value, window
from agent.ontology import CATALOGUE_GRAPH, CLOSURE_GRAPH, OREXIS, ROLE, SELF_GRAPH
from agent.store import (NAMESPACES, answer, catalogue_of, close_catalogue, closed, classify, document, forget_graph,
                         graphs_of, imports_of, kinds_in, put_document, rows, update, whose, DocumentRefused, Raw)

log = logging.getLogger("runtime")

KERNEL = Path(__file__).resolve().parent
ASSERTED = OREXIS + "Asserted"
DERIVED = OREXIS + "Derived"
ONTOLOGY = OREXIS + "OntologyGraph"
WORLD = OREXIS + "WorldGraph"
SOCIETY = OREXIS + "SocietyGraph"
PUBLIC = OREXIS + "PublicGraph"
GRAPH = OREXIS + "Graph"


#  WHAT THE RUNTIME SAYS HAPPENED, its own two events.


@dataclasses.dataclass(frozen=True)
class Written:
    """A graph written — by a job, a handler, or a package mid-act — and every kind it is."""
    graph: str
    kinds: frozenset


_STARTED = time.perf_counter()


@dataclasses.dataclass(frozen=True)
class Passed:
    """A pass, in real seconds, whole and by part — the jobs queued run to the last (`drain`),
    planning, walking; a part a pass does not reach is not in it, and the planner's own parts are
    its event — with how large the belief base is, in quads, and how long the process has run."""
    metric = "pass"
    duration_s: Value
    drain_s: Value = None
    plan_s: Value = None
    execute_s: Value = None
    quads: Level = None
    uptime_s: Level = None


DOCUMENTS = (".ttl", ".trig")

#  WHERE A WORLD KEEPS WHAT IS NOT COMMITTED — credentials, and a document such as where its place is.
SECRETS = "secrets"
BELIEFS = "beliefs"

#  A PACKAGE IS A DIRECTORY OF `agent/` HOLDING AN `ontology.ttl` — rule 2's package, found by
#  looking and never listed: the roles it serves are declared there, and so is every word it owns.
#  It is named by its directory, which is what `packages_of` answers and `parts` is keyed by.
VOCABULARY = "ontology.ttl"
MQTT, HTTP = "transport/mqtt", "transport/http"
#  THE ONE PACKAGE THE BOOT ITSELF CALLS INTO, where it is loaded: the planner writes the scopes.
PLANNING = "planning"

#  WHERE EACH LOADED PART STANDS IN A PASS, and nothing else: WHICH packages load is the agent's
#  roles' to say, and this only orders the ones that do, as their parts are created and started.
#  Belief first, so its rules have concluded of a graph written before anything else hears it; the
#  planner's pass before the executor's walk, which takes what the pass published; then what
#  answers the world — sensing's ask, prediction's answer to an observation — and speech, and the
#  transports last. A package not named here is still found and loaded where a role calls for it,
#  after these, by its name.
PASS = ("belief", "planning", "execution", "sensing", "prediction", "speech", MQTT, HTTP)

#  A SENSOR OF THE AGENT'S: hosted by what it acts for, by a sample of it, or by a place that
#  contains it — the one relation sensing's callers read a sensor as the agent's by (the MQTT
#  driver's `open` and `handle`, the HTTP driver's, sensing's `missed` of a series), and the one
#  the observer's shape asks for.
MINE = ("?me orexis:actsFor ?subject . ?subject schema:containedInPlace* ?host . "
        "?sensor sosa:isHostedBy/(sosa:isSampleOf)? ?host .")

#  THE ROLES THAT NEED BYTES, which the transports are loaded for: a transport is no role and no
#  author declares one, so it is the one derivation left — where a loaded role needs bytes and the
#  society wires a bus, which device a bus reaches being wiring and not a choice. For each
#  transport, the role and a pattern about `?me` asked over the world's public graphs and the self:
#  - THE MQTT TRANSPORT, for an observer one of whose sensors publishes on a topic, and for a speaker
#    listening to one — what the member subscribes to. Where the agent commands an actuator and
#    neither holds, no member is loaded: which actuators are the agent's is a domain's word;
#  - THE HTTP TRANSPORT, for an observer one of whose sensors is a thing with a form (WoT's
#    `td:hasForm`) — a service it fetches, a forecast.
#  Every word here is a T-Box term and the world's things are variables, so nothing here names an
#  instance (rule 1).
OBSERVER, SPEAKER = NAMESPACES["sensing"] + "Observer", NAMESPACES["speech"] + "Speaker"
TRANSPORTS = {
    MQTT: {OBSERVER: f"{MINE} ?sensor mqtt4ssn:observesTopic ?topic",
           SPEAKER: "?me mqtt4ssn:listensToTopic ?topic"},
    HTTP: {OBSERVER: f"{MINE} ?sensor td:hasForm ?form"},
}
#  WHAT WATCHES THE AGENT: a package created where the environment names a store for it, which is a
#  fact of deployment and not of the world, so no role decides it (`agent.series`).
WATCHERS = ("history", "metrics")

#  WHO THIS PROCESS IS: the AGENT with the id it was told. The id alone is not enough — the
#  sensing world's fern and the agent acting for it share one — so the kind is asked too. Asked
#  of the society graph, where a world with a bus states its principals, and of the world graph,
#  where a world with none states its one agent beside what it acts on.
_ME_Q = "SELECT ?me WHERE { ?me a orexis:Agent ; orexis:localId $id }"
#  EVERY KIND THE SELF IS STATED, in its self graph: `orexis:Self` and the roles beside it.
_DECLARED_Q = "SELECT DISTINCT ?kind WHERE { ?me a orexis:Self , ?kind }"
_SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_CLASS = "http://www.w3.org/2002/07/owl#Class"
#  EVERY AGENT THE WORLD STATES, where the same two graphs state them: whom a graph of an agent's
#  own may say it is.
_AGENTS_Q = "SELECT DISTINCT ?a WHERE { ?a a orexis:Agent }"
#  EVERY SELF THE STORE HOLDS, in any graph at all — COUNTED, never picked: a self in a graph the
#  boot did not put in is a self all the same to a text that asks for one.
_SELVES_Q = "SELECT DISTINCT ?self WHERE { GRAPH ?g { ?self a orexis:Self } } ORDER BY ?self"
#  WHAT A BOOT PUT IN AND NOBODY HOLDS: asserted from a document, with no owner — the kernel's,
#  the packages' and the world's public graphs — and the closure derived from them.
_FILES_Q = """
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  { ?g orexis:arrivedBy orexis:Asserted FILTER NOT EXISTS { ?g orexis:beliefsOf ?who } }
  UNION { VALUES ?g { $closure } ?g orexis:arrivedBy ?any } FILTER(?g != ?cat) } }"""
_CLOSE_U = """
INSERT {{ GRAPH <{closure}> {{ ?a rdfs:subClassOf ?c }} }}
{using}
WHERE  {{ ?a rdfs:subClassOf+ ?c FILTER(isIRI(?a) && isIRI(?c) && ?a != ?c) }}"""


def documents(world: Path, packages=None) -> list[Path]:
    """What a boot reads: the kernel's T-Box first, then the documents of `packages` — every
    package of the tree where none are named, which is what the operator's tools read — then every document in the
    world's directory, under its `secrets/` and under its `beliefs/`. Found by looking, never
    listed, and never a test's.

    A DOCUMENT IN THE WORLD'S `secrets/` IS READ LIKE ONE BESIDE IT: what the world keeps out of
    the repository — where its place is — is still the world's, and a world without it boots.

    `beliefs/` IS WHERE A WORLD KEEPS ITS AGENTS' OWN DOCUMENTS, and the name is for eyes: every
    document there is read, and whose each graph is, is what the graph says (`store.whose`). A
    world of several agents states each one's desires apart, because the derivation mints a want
    under every desire a store holds — kept by content, a bidder's desire stands in its own store
    and not its host's, whatever the file is called."""
    def under(directory: Path) -> list[Path]:
        return sorted(p for p in directory.glob("*") if p.is_file() and p.suffix in DOCUMENTS)
    world = Path(world)
    packages = every_package() if packages is None else packages
    return [KERNEL / "ontology.ttl", *_documents_of(packages), *under(world), *under(world / SECRETS), *under(world / BELIEFS)]


def _documents_of(packages) -> list[Path]:
    """Every document in the directories of `packages`, their tests' cases apart."""
    return [p for package in packages for p in sorted((KERNEL / package).rglob("*"))
            if p.suffix in DOCUMENTS and "tests" not in p.relative_to(KERNEL / package).parts]


@cache
def every_package() -> tuple[str, ...]:
    """Every package of the tree — each directory of `agent/` but the kernel's own holding an
    `ontology.ttl`, its tests' apart — in the order a pass runs their parts (`PASS`), and any
    package that order does not name after, by its name. Found by looking, never listed."""
    found = {p.parent.relative_to(KERNEL).as_posix() for p in KERNEL.rglob(VOCABULARY)
             if p.parent != KERNEL and "tests" not in p.relative_to(KERNEL).parts}
    return tuple(sorted(found, key=lambda package: (PASS.index(package) if package in PASS else len(PASS), package)))


@cache
def _vocabularies() -> tuple[dict[str, str], dict[str, frozenset[str]]]:
    """What every package's ontology says of roles, READ APART — never put into an agent's store,
    since which packages' documents go in is what this decides: each role a package declares, with
    the package, and every `rdfs:subClassOf` step the packages' ontologies state, by class. A class
    is a role where those steps reach `orexis:Role`, and it is the role of the package whose
    ontology declares it an `owl:Class` — the directory it was read from, which is a package by
    rule 2 and no instance. Hanoi's store holding no sensing ontology is what reading them apart
    keeps (#824)."""
    above: dict[str, set[str]] = {}
    declared: dict[str, str] = {}
    for package in every_package():
        doc = document(KERNEL / package / VOCABULARY)
        for q in doc.quads_for_pattern(None, ox.NamedNode(_SUBCLASS), None, None):
            if isinstance(q.subject, ox.NamedNode) and isinstance(q.object, ox.NamedNode):
                above.setdefault(q.subject.value, set()).add(q.object.value)
        for q in doc.quads_for_pattern(None, ox.NamedNode(_TYPE), ox.NamedNode(_CLASS), None):
            if isinstance(q.subject, ox.NamedNode):
                declared.setdefault(q.subject.value, package)
    steps = {cls: frozenset(supers) for cls, supers in above.items()}
    return {cls: package for cls, package in declared.items() if ROLE in _beneath(cls, steps)}, steps


def _beneath(cls: str, steps, store: ox.Store | None = None) -> set[str]:
    """`cls` and every class it is beneath, by the packages' own steps (`steps`) and, where a store
    is given, by the closure the store holds — a domain's role is beneath a package's by a step the
    domain states, and a package's beneath `orexis:Role` by a step only its own ontology states."""
    reached, frontier = set(), {cls}
    while frontier:
        c = frontier.pop()
        if c in reached:
            continue
        reached.add(c)
        frontier |= set(steps.get(c, ())) | (set(closed(store, c)) if store is not None else set())
    return reached


def roles_of(store: ox.Store) -> frozenset[str]:
    """Every role the self of `store` is in: each kind its self graph states it beside
    `orexis:Self`, and every class those are beneath, that is beneath `orexis:Role` — read off the
    self graph alone, as a stance is, since a role is the agent's word about itself and nothing a
    peer or the public world may say of it. Empty where it declares none."""
    _, steps = _vocabularies()
    stated = {r["kind"] for r in rows(store, _DECLARED_Q, graphs_of(store, SELF_GRAPH))}
    reached = set().union(*(_beneath(kind, steps, store) for kind in stated)) if stated else set()
    return frozenset(c for c in reached if c != ROLE and ROLE in _beneath(c, steps, store))


def packages_of(store: ox.Store) -> tuple[str, ...]:
    """Every package the self of `store` loads, in the order a pass runs their parts: each package
    whose ontology declares a role the self is in (`roles_of`), and each transport a loaded role
    needs bytes from (`TRANSPORTS`), asked over the world's public graphs and the self. Nothing
    where the self declares no role — no default and no fixed mind
    (a-package-is-loaded-only-for-a-role-the-agent-is-declared-in)."""
    roles = roles_of(store)
    serving, _ = _vocabularies()
    loaded = {package for role, package in serving.items() if role in roles}
    known = graphs_of(store, PUBLIC, SELF_GRAPH)
    for transport, needs in TRANSPORTS.items():
        if any(role in roles and answer(store, f"ASK {{ ?me a orexis:Self . {pattern} }}", known)["boolean"]
               for role, pattern in needs.items()):
            loaded.add(transport)
    return tuple(package for package in every_package() if package in loaded)


def known(store: ox.Store, kinds) -> bool:
    """Whether the vocabulary in `store` declares one of `kinds` a kind of graph — whether a reader
    holding that vocabulary reads the graph. A kind is declared where the closure puts it beneath
    `orexis:Graph`; anything else, a kind another reader declares or a kind misspelled, is not."""
    return any(GRAPH in closed(store, kind) for kind in kinds)


def read_with_imports(paths: list[Path]) -> list[tuple[Path, ox.Store]]:
    """Every document `paths` names and every one they import, each read once, in the order
    met: a world imports the domains it speaks, and a domain its own documents. An import that
    is no `file:` IRI names nothing a boot can read, and stays a row in the catalogue."""
    read, seen, queue = [], set(), [p.resolve() for p in paths]
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        doc = document(path)
        read.append((path, doc))
        for iri in imports_of(doc):
            if iri.startswith("file:"):
                queue.append(Path(unquote(urlparse(iri).path)).resolve())
    return read


def _forget_the_files(store: ox.Store) -> None:
    """A volume lived in: every graph a document put in and nobody holds goes, rows and all,
    and the closure with them, since every one of them is read again."""
    for row in rows(store, _FILES_Q, (), closure=CLOSURE_GRAPH):
        forget_graph(store, row["g"])


def _close_vocabulary(store: ox.Store) -> None:
    """Every `rdfs:subClassOf` step the ontology graphs reach, into the closure graph, so that
    one step is every step (one-graph-both-engines-read) and `closed` walks no path. Asked over
    every ontology graph at once, since a world's class may sit beneath a package's."""
    vocabularies = graphs_of(store, ONTOLOGY)
    using = "\n".join(f"USING <{g}>" for g in vocabularies)
    forget_graph(store, CLOSURE_GRAPH)
    update(store, _CLOSE_U.format(closure=CLOSURE_GRAPH, using=using))
    classify(store, CLOSURE_GRAPH, ONTOLOGY, DERIVED)


def _put_public(store: ox.Store, world: Path, agent_id: str | None = None,
                others: frozenset[str] = frozenset()) -> list[tuple[ox.Store, str]]:
    """Read the documents and put in the vocabulary, closed, and every public graph; for an agent,
    put in its self graph and answer the world's other graphs that say they are this agent's as
    (document, graph), for the caller to put or not. With no agent, nothing private is answered,
    and no self is put: every graph of an agent's own is still held to naming an agent of the
    world, so a world whose documents a tool reads whole is refused where an agent's boot would be.

    THE VOCABULARY FIRST, since whether a graph is public is the vocabulary's to say — and so is
    whether it is read at all. A graph whose kind the vocabulary does not declare is passed over:
    a document of a kind another reader reads, onboarding's hardware, is not this agent's to hold,
    and what keeps it out is that nothing it loads says what the kind is
    (a-documents-kind-says-who-reads-it). A misspelled kind is passed over the same way, which is
    why onboarding, knowing every reader's vocabulary, refuses a world that holds one.

    THE KERNEL AND THE WORLD FIRST, AND A PACKAGE FOR A ROLE. For an agent, the kernel and the world
    go in first — the domains it imports among them, whose roles sit beneath the packages' — then the
    self, and its roles are read off its self graph (`roles_of`), so nothing waits on the package it
    decides. The documents of the packages those roles call for go in next (`packages_of`), and a
    world graph passed over for a kind only such a package declares is looked at again. With no
    agent, every package is read at once: the operator's tools read every reader's vocabulary.

    WHAT IS PASSED OVER IS SAID, and quietly only for a kind in `others`: the kinds a caller
    declares itself and reads next, onboarding's for a world it reads as the first half of its
    own read. Anything else is a kind no reader declares, or one this reader cannot tell from
    it, and that is logged where it is seen."""
    read = read_with_imports(documents(world, () if agent_id else None))
    own, passed = _put(store, world, read, [])
    own = _owned(store, own)
    if agent_id:
        close_catalogue(store)          # the rows say every kind they are beneath, so a transport's need reads the public graphs
        me = _identity(store, agent_id)
        self_graph = _hold_the_self(store, agent_id, me, [(doc, graph) for doc, graph, owner in own if owner == me])
        loaded = packages_of(store)     # off the self graph, which states the roles
        seen = {path for path, _ in read}
        more = [(path, doc) for path, doc in read_with_imports(_documents_of(loaded)) if path not in seen]
        if more:
            also, passed = _put(store, world, more, passed)
            own += _owned(store, also)
        if loaded:
            log.info("%s loads %s", agent_id, ", ".join(loaded))
        else:
            log.warning("%s is declared in no role, so it loads no package and runs nothing: its self graph "
                        "says what it runs, `<agent> a orexis:Self , <role>`", agent_id)
    for _path, _doc, graph, kinds in passed:
        log.log(logging.DEBUG if others & set(kinds) else logging.INFO,
                "passed over %s: %s is no kind this agent reads", graph, ", ".join(sorted(kinds)))
    if not agent_id:
        return []
    for _doc, graph, owner in own:
        if owner != me:
            log.debug("%s is %s's and not this agent's", graph, owner)
    return [(doc, graph) for doc, graph, owner in own if owner == me and graph != self_graph]


def _owned(store: ox.Store, own) -> list[tuple[ox.Store, str, str]]:
    """Each graph of an agent's own in `own`, (document, graph), with whose its document says it
    is (`store.whose`) — refused where it says nobody's, or the name of no agent the world states:
    a graph kept by its owner and owned by nobody would be every agent's or none's, silently."""
    agents = {r["a"] for r in rows(store, _AGENTS_Q, graphs_of(store, SOCIETY, WORLD))}
    out = []
    for doc, graph in own:
        owner = whose(doc, graph)
        if owner is None:
            raise DocumentRefused(f"{graph} is of a kind that is some agent's own and says nobody's — "
                                  f"`<> orexis:beliefsOf <agent>` says whose")
        if owner not in agents:
            raise DocumentRefused(f"{graph} says it is {owner}'s, and the world states no such agent")
        out.append((doc, graph, owner))
    return out


def _put(store: ox.Store, world: Path, read, passed) -> tuple[list, list]:
    """Put the vocabulary `read` holds and close it, then every public graph of `read`, and of
    what was `passed` over before, whose kind the vocabulary now declares — refused where one
    says whose it is, since a public graph is everyone's. The world's graphs of an agent's own
    as (document, graph), and what is passed over still as (path, document, graph, kinds)."""
    vocabulary = {path for path, doc in read if any(ONTOLOGY in k for k in kinds_in(doc).values())}
    for path, doc in read:
        if path in vocabulary:
            put_document(store, doc)
    _close_vocabulary(store)
    candidates = [(path, doc, graph, kinds) for path, doc in read if path not in vocabulary
                  for graph, kinds in kinds_in(doc).items()]
    public, own, still = [], [], []
    for path, doc, graph, kinds in [*passed, *candidates]:
        if not known(store, kinds):
            still.append((path, doc, graph, kinds))
            continue
        beneath = {k for kind in kinds for k in closed(store, kind)}
        if world not in path.parents or PUBLIC in beneath:
            if PUBLIC in beneath and whose(doc, graph) is not None:
                raise DocumentRefused(f"{path.name} says whose {graph} is, and a graph of "
                                      f"{', '.join(sorted(kinds))} is public, everyone's and nobody's own")
            public.append((doc, graph))
        else:
            own.append((doc, graph))
    for doc, graph in public:
        put_document(store, doc, graphs={graph})
    return own, still


def world_of(world: Path, others=frozenset()) -> ox.Store:
    """What a world says publicly, read as a boot reads it and closed, with no agent in it — what
    the simulator reads, and what the operator's tools read before the kinds they read and no
    agent does: its agents, its devices, its topics — and never where its broker listens, which
    is a deployment graph, a kind only onboarding reads. With no agent there are no roles to read,
    so every package's documents are read: this is every reader's world, not one agent's.
    A graph of a kind in `others`, which the caller reads itself, is passed over at DEBUG."""
    store = ox.Store()
    update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph , orexis:Graph }} }}")
    _put_public(store, Path(world).resolve(), others=frozenset(others))
    close_catalogue(store)
    return store


def boot(world: Path, agent_id: str, store: ox.Store | None = None, others=frozenset()) -> ox.Store:
    """The agent's store from the documents: every graph classified by the document that holds
    it, the vocabulary closed, the catalogue closed, the scopes written. Handed a store that
    already holds a catalogue, read again every graph nobody owns and leave the agent's own.
    A graph of a kind in `others` is passed over at DEBUG, as `world_of` does: a caller booting
    an agent to ask what it holds, onboarding, reads those kinds itself."""
    world = Path(world).resolve()
    store = store if store is not None else ox.Store()
    lived_in = catalogue_of(store) is not None
    if lived_in:
        _forget_the_files(store)
    else:
        update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph , orexis:Graph }} }}")
    own = _put_public(store, world, agent_id, others=frozenset(others))
    me = _identity(store, agent_id)
    if not lived_in:
        for doc, graph in own:
            put_document(store, doc, owner=me, graphs={graph})
    close_catalogue(store)
    #  THE SCOPES ARE THE PLANNER'S, written once the vocabulary is in, and only where the agent runs
    #  one: imported here and nowhere else, so a process that plans nothing imports no Planner.
    if PLANNING in packages_of(store):
        from agent.planning.planner import Planner
        Planner.scope(store)
    log.info("%s booted from %s%s", agent_id, world, " (a volume lived in: its own graphs kept)" if lived_in else "")
    return store


def _identity(store: ox.Store, agent_id: str) -> str:
    found = rows(store, _ME_Q, graphs_of(store, SOCIETY, WORLD), id=ox.Literal(agent_id))   # a str binds as an IRI; the id is a literal
    if len(found) != 1:
        raise RuntimeError(f"the world says {'nobody' if not found else 'several agents'} is {agent_id!r}")
    return found[0]["me"]


def selves(store: ox.Store) -> list[str]:
    """Every agent the store says is the self, in any graph, sorted — one in an agent's store, none
    in a store holding a whole world, and anything else a store no boot will run."""
    return [r["self"] for r in rows(store, _SELVES_Q)]


def _hold_the_self(store: ox.Store, agent_id: str, me: str, mine) -> str:
    """The self, checked and never minted: of `mine` — the graphs of `me`'s own, (document,
    graph), which `me` is the agent this process was told to be — exactly one is a self graph,
    and it is put in, owned and asserted, where the store holds no self: a fresh store, or a
    volume lived in before the self was authored. A volume lived in keeps the one it has. The
    self graph's name.

    REFUSED, NEVER PICKED. No self graph of the agent's, or two, is a world that has not said who
    the agent is, once; a volume whose self is another agent is the right id handed the wrong
    volume, and is not lived in by somebody else; a store saying two agents are the self would
    have every text asking `?me a orexis:Self` answer for both, silently. None of them boots. The
    gate stands here, once, and not in each text."""
    authored = [(doc, graph) for doc, graph in mine if SELF_GRAPH in kinds_in(doc)[graph]]
    if len(authored) != 1:
        said = (f"no self graph of the world says who {agent_id!r} is" if not authored else
                f"{len(authored)} self graphs of the world say who {agent_id!r} is "
                f"({', '.join(sorted(g for _, g in authored))})")
        raise RuntimeError(f"{said}: a world authors one for each of its agents, and the boot checks it "
                           f"and never writes one")
    (doc, graph), = authored
    if not selves(store):
        put_document(store, doc, owner=me, graphs={graph}, close=True)
    held = selves(store)
    if held != [me]:
        raise RuntimeError(
            f"this store's self is {held[0]}, and the process was told to be {agent_id!r}: a volume is "
            f"one agent's, and it is not lived in by another" if len(held) == 1 else
            f"this store says {len(held)} agents are the self ({', '.join(held)}): a self is one, and a "
            f"text asking for it would answer for all of them")
    return graph


class Runtime:
    """One agent's process: a lifecycle container for its packages, run pass by pass.

    A PACKAGE HAS A PART, CREATED, LINKED AND STARTED (a-package-starts-itself, `agent.lifecycle`).
    Every package the agent loads — each its declared roles call for, and the transports they need —
    that has a `create` module makes its part; then each part links to the others, connecting its own signals
    to what lies beneath it; then each starts: belief revises what is written, planning plans every
    pass, execution walks what is due, a transport listens or polls, sensing asks after silence,
    prediction answers an observation. The parts are kept in `parts`, by package, and the runtime
    knows no word of what any of them do.

    WHAT IT OFFERS A PART. `submit` a job from any thread; `every` so many seconds of the one
    timeline; `on` a kind of graph written — the one signal it owns — and `wrote`, for graphs written
    outside a job; `hold` the agent alive or `release` it with an outcome; `again`, to pass once more
    without waiting; and `lap` a part of the pass. Every job and every handler runs on this
    one thread, one at a time.

    A transport package is started only where the runtime is told to `connect`, which is the
    process's `main`; a test hands a member brought up, and it is started the same way."""

    def __init__(self, beliefs: ox.Store, agent_id: str, *, budget: int | None = None,
                 intentions: ox.Store | None = None, transport=None, connect: bool = False):
        self.beliefs, self.id = beliefs, agent_id
        self.me = _identity(beliefs, agent_id)
        self.packages = packages_of(beliefs)
        #  WHAT PLANNING AND EXECUTION ARE HANDED: a search's budget only where a caller sizes one — a
        #  test; otherwise None, and the Planner reads the agent's stance — and the intentions' store.
        self.budget, self.intentions = budget, intentions
        self._laps: Laps | None = None                    # the parts of the pass in progress, where heard
        self._jobs: queue.SimpleQueue = queue.SimpleQueue()
        self.written = Signal("written")                  # a graph written, and its kinds
        self.passed = Signal("passed")                    # a pass, where anybody hears it
        self._timers: list[list] = []                     # [seconds, next due or None, job]
        self._stops: list = []
        self._members: list = []
        self._held: dict = {}                             # who keeps the agent alive
        self._outcome: str | None = None
        self._again = False
        self.now = None                                   # the instant the pass stands at, for a job to read
        self.parts: dict[str, object] = {}
        self._assemble(transport, connect)

    # ── what a package is offered ──────────────────────────────────────────────────────────────

    def submit(self, job) -> None:
        """Queue `job` — a callable answering the graphs it wrote — to run on this thread, from any
        thread: a transport's listener hands its message on this way."""
        self._jobs.put(job)

    def every(self, seconds: float, job) -> None:
        """Run `job` at the first pass and again every `seconds` of the one timeline after — every
        pass where `seconds` is nought: the runtime does the waiting, and the package says only
        what it waits for. Timers run after the jobs queued, in the order they were asked for."""
        self._timers.append([float(seconds), None, job])

    def on(self, kind: str, handler) -> None:
        """Run `handler(graph)` — answering the graphs it wrote in turn — for every graph of `kind`
        written: how a package answers another's work with neither naming the other, the belief base
        being the interface between them. The one signal the runtime owns."""
        self.written.connect(lambda written: handler(written.graph) if kind in written.kinds else ())

    def wrote(self, graphs) -> None:
        """Say that `graphs` were written — by a job, a handler, or a package mid-act — so that
        whoever listens for their kinds hears it now, and what they write in turn."""
        for graph in graphs:
            self.wrote(self.written.emit(Written(graph, frozenset(self._kinds(graph)))))

    def hold(self, who) -> None:
        """`who` keeps the agent running: a desire, a listening transport."""
        self._held[who] = True

    def release(self, who, outcome: str | None = None) -> None:
        """`who` no longer keeps the agent running, and says how its part ended; the run ends when
        nobody holds it."""
        self._held.pop(who, None)
        if outcome is not None:
            self._outcome = outcome

    def again(self) -> None:
        """Pass once more at once, without waiting the poll: something moved, or a search was cut short."""
        self._again = True

    def lap(self, part: str) -> None:
        """Mark the end of a part of the pass, for the pass's event."""
        if self._laps is not None:
            self._laps(part)

    def attach(self, member) -> None:
        """A transport member brought up and started; held behind the family's `Transports` where
        there are several, for a test that hands a message to it (`deliver`)."""
        self._members.append(member)

    @property
    def transport(self):
        if len(self._members) > 1:
            from agent.transport.transport import Transports     # the family, only where a member is loaded
            return Transports(self._members)
        return self._members[0] if self._members else None

    def deliver(self, channel, payload: bytes, at) -> None:
        """A message for the transport, as its thread would hand it: queued, to be handled on this one."""
        transport = self.transport
        self.submit(lambda: [graph for _, graph in transport.handle(self.beliefs, channel, payload, at)])

    # ── the lifecycle ────────────────────────────────────────────────────────────────────────

    def drain(self, now) -> None:
        """Run every job queued, and what their writes set off, until none is left; then what is
        due at `now`, the same way."""
        self.now = now
        self._run_jobs()
        self.lap("drain")
        for timer in self._timers:
            seconds, due, job = timer
            if due is None or now >= due:
                timer[1] = now + timedelta(seconds=seconds)
                self.submit(job)
        self._run_jobs()

    def _run_jobs(self) -> None:
        while True:
            try:
                job = self._jobs.get_nowait()
            except queue.Empty:
                return
            self.wrote(job() or ())

    def run(self, *, passes: int | None = None, poll_s: float = 1.0) -> str:
        """Pass after pass until nobody holds the agent — ending as the last to let go said, `met`
        or `unreachable` — or `passes` ran out (`unfinished`). A pass that moved nothing waits the
        poll before the next, unless a package asked to go `again`."""
        n = 0
        while passes is None or n < passes:
            n += 1
            now = clock.now()
            #  THE PASS'S PARTS, in real seconds, kept where anybody hears the pass — by
            #  `perf_counter`, never the clock.
            self._laps = Laps() if self.passed.connected else None
            self._again = False
            started = time.perf_counter()
            self.drain(now)
            self._passed(time.perf_counter() - started)
            if not self._held:
                log.info("%s: nothing holds it, after %d pass(es)", self.id, n)
                return self._outcome or MET
            if not self._again:
                time.sleep(poll_s)
        return UNFINISHED

    def stop(self) -> None:
        """Stop every package started, the last first."""
        while self._stops:
            self._stops.pop()()

    def _assemble(self, transport, connect: bool) -> None:
        """A package's life in three phases (`agent.lifecycle`): every package that has a `create`
        module creates its part, in the order of a pass (`PASS`) — a transport package only where the runtime is told
        to `connect`, a member handed in standing for it; then every part links to the others; then
        every part starts, and its stop is kept for the end."""
        #  WHAT WATCHES THE AGENT, where the environment names a store for it — last, so it is linked
        #  to every part and stopped first, writing the last window.
        watchers = [name for name, purpose in zip(WATCHERS, (series.HISTORY, series.METRICS))
                    if series.sink(purpose) is not None]
        for package in [*self.packages, *watchers]:
            name = "agent." + package.replace("/", ".") + ".create"
            if package.startswith("transport/") and (transport is not None or not connect):
                continue
            if importlib.util.find_spec(name) is None:
                continue
            self.parts[package] = importlib.import_module(name).create(self)
        if transport is not None:
            self.parts["transport"] = transport
        for part in self.parts.values():
            if callable(getattr(part, "link", None)):
                part.link(self.parts)
        for part in self.parts.values():
            if callable(getattr(part, "start", None)):
                part.start(self)
            if callable(getattr(part, "stop", None)):
                self._stops.append(part.stop)

    def _kinds(self, graph: str) -> set[str]:
        cat = catalogue_of(self.beliefs)
        return {r["k"] for r in rows(self.beliefs, "SELECT ?k WHERE { GRAPH $cat { $g a ?k } }", (),
                                     cat=Raw(f"<{cat}>"), g=graph)}

    def _passed(self, took: float) -> None:
        """Say the pass, where anybody hears it."""
        if self._laps is None:
            return
        self.passed.emit(Passed(duration_s=round(took, 6), **self._laps.spent, quads=len(self.beliefs),
                                uptime_s=round(time.perf_counter() - _STARTED, 3)))


def world_name(world: Path) -> str:
    """The name a world goes by outside the agent: its directory's, as onboarding names it."""
    return Path(world).resolve().name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One agent of Agent 0.2.0, booted from a world's files and run until nothing is left to pursue.")
    parser.add_argument("world", type=Path, help="the world's directory")
    parser.add_argument("agent", help="this agent's id — the one identifier a process is told")
    parser.add_argument("--volume", type=Path, help="where the store persists; in memory when absent")
    parser.add_argument("--passes", type=int, help="stop after this many passes whatever stands")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    store = ox.Store(str(args.volume)) if args.volume else None
    beliefs = boot(args.world, args.agent, store)
    #  A SINK PER PURPOSE THE ENVIRONMENT NAMES A STORE FOR, and the part that writes it created with
    #  the rest: history as events happen, metrics once a window, as long as the environment says.
    told = series.load()
    interval = window.load()
    log.info("%s writes %s", args.agent, ", ".join(p.lower() for p in told) + " to a series store" if told else "no series")
    if window.recording():
        log.info("%s writes its metrics every %gs", args.agent, interval)
    #  WHO SPEAKS, on every metric point: the agent's id, which the process is told, and the name of
    #  the world's directory, which it is handed — the name its buckets, its compose project and its
    #  dashboards' folder go by. Neither is an instance the code names: both arrive as arguments.
    window.identify(world=world_name(args.world), agent=args.agent)
    #  NO BUDGET IS HANDED: how much a search may spend is the agent's stance, in its self graph, and a
    #  flag beside it would be a second place the figure lives (knowledge/domain/kernel/stance.md).
    runtime = Runtime(beliefs, args.agent, connect=True)
    #  A STOP IS AN EXIT, so every part is stopped and the last window written: `podman stop` sends
    #  SIGTERM, whose default ends the process where it stands and would lose up to a window of metrics.
    signal.signal(signal.SIGTERM, _stopped)
    try:
        outcome = runtime.run(passes=args.passes)
    finally:
        runtime.stop()
    return {MET: 0, UNREACHABLE: 1, UNFINISHED: 2}[outcome]


def _stopped(signum, frame) -> None:
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    sys.exit(main())

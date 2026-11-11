"""What a world's documents say, read as the agent reads them: the part of a boot the operator's tools and the simulator
still do in Python. The agent itself is `crates/orexis-agent/`; `onboarding.reading.boot` asks it for the store it will run on, and what
is here is what is asked BEFORE an agent exists or with none in it — a world read whole, which documents a boot takes, which
packages a role loads."""

from __future__ import annotations

import logging
from functools import cache
from pathlib import Path
from urllib.parse import unquote, urlparse

import pyoxigraph as ox

from .ontology import BELIEF, CATALOGUE_GRAPH, CLOSURE_GRAPH, DERIVED, OREXIS, ROLE, SELF_GRAPH
from .store import (answer, classify, close_catalogue, closed, document, forget_graph, graphs_of, imports_of, kinds_in,
                    put_document, rows, update, whose, DocumentRefused)

log = logging.getLogger("documents")


#  THE TREE, `crates/`: a crate per package beside the kernel's, `crates/orexis/`, each named for its package —
#  `transport/mqtt` is `crates/orexis-transport-mqtt/` (`directory_of`).
TREE = Path(__file__).resolve().parent.parent / "crates"

KERNEL = TREE / "orexis"


def directory_of(package: str) -> Path:
    """A package's directory, a crate of the tree: `transport/mqtt` is `orexis-transport-mqtt`."""
    return TREE / f"{KERNEL.name}-{package.replace('/', '-')}"


def package_of(directory: str) -> str | None:
    """The package a directory of the tree is, where it is one: `orexis-transport-mqtt` is `transport/mqtt`."""
    prefix = KERNEL.name + "-"
    return directory[len(prefix):].replace("-", "/", 1) if directory.startswith(prefix) else None

ONTOLOGY = OREXIS + "OntologyGraph"

WORLD = OREXIS + "WorldGraph"

SOCIETY = OREXIS + "SocietyGraph"

GRAPH = OREXIS + "Graph"

DOCUMENTS = (".ttl", ".trig")

#  WHERE A WORLD KEEPS WHAT IS NOT COMMITTED: a directory per agent, named by its id, holding the agent's
#  credentials and every document only it is handed — where its place is, which chat is its; and beside them what
#  is no agent's, the authority and the boards (an-agent-keeps-its-secrets-in-a-directory-of-its-own).
SECRETS = "secrets"

BELIEFS = "beliefs"

#  A PACKAGE IS A CRATE OF `crates/` HOLDING AN `ontology.ttl` — rule 2's package, found by
#  looking and never listed: the roles it serves are declared there, and so is every word it owns.
#  It is named by its directory, which is what `packages_of` answers and `parts` is keyed by.
VOCABULARY = "ontology.ttl"

MQTT, HTTP, TELEGRAM, EMAIL = "transport/mqtt", "transport/http", "transport/telegram", "transport/email"

#  WHERE EACH LOADED PART STANDS IN A PASS, and nothing else: WHICH packages load is the agent's
#  roles' to say, and this only orders the ones that do, as their parts are created and started.
#  Belief first, so its rules have concluded of a graph written before anything else hears it; the
#  planner's pass before the executor's walk, which takes what the pass published; then what
#  answers the world — sensing's ask, prediction's answer to an observation — and speech, and the
#  transports last. A package not named here is still found and loaded where a role calls for it,
#  after these, by its name.
PASS = ("belief", "planning", "execution", "sensing", "prediction", "speech", "translation", "coordination", MQTT, HTTP,
        TELEGRAM, EMAIL)

#  A SENSOR OF THE AGENT'S: one an observer role it plays reads (`sensing:sensor`), DECLARED, so
#  nothing here walks where a sensor is mounted; onboarding holds the declaration to the world
#  (`crates/orexis-sensing/ontology.ttl`'s observer shape). The one relation the transports read a sensor as
#  the agent's by, the MQTT driver's and the HTTP driver's, and named here for the patterns below.
MINE = "?me orexis:plays/sensing:sensor ?sensor ."

#  THE ROLES THAT NEED BYTES, which the transports are loaded for: a transport is no role and no
#  author declares one, so it is the one derivation left — where a loaded role needs bytes and the
#  society wires a bus, which device a bus reaches being wiring and not a choice. For each
#  transport, the role and a pattern about `?me` asked over the world's common graphs and the self:
#  - THE MQTT TRANSPORT, for an observer one of whose sensors publishes on a topic, and for a speaker
#    listening to one — what the member subscribes to. Where the agent commands an actuator and
#    neither holds, no member is loaded: which actuators are the agent's is a domain's word;
#  - THE HTTP TRANSPORT, for an observer one of whose sensors is a thing with a form (WoT's
#    `td:hasForm`) — a service it fetches, a forecast.
#  Every word here is a T-Box term and the world's things are variables, so nothing here names an
#  instance (rule 1).
_PACKAGE_TERMS = "http://example.org/orexis/"

OBSERVER, SPEAKER = _PACKAGE_TERMS + "sensing#Observer", _PACKAGE_TERMS + "speech#Speaker"
TRANSLATOR = _PACKAGE_TERMS + "translation#Translator"

#  A CHAT THE AGENT IS IN, through a channel of the kind a member carries (`speech:Chat`).
_IN_A_CHAT = "?chat speech:participant ?me ; speech:channel ?channel . "

TRANSPORTS = {
    MQTT: {OBSERVER: f"{MINE} ?sensor mqtt4ssn:observesTopic ?topic",
           SPEAKER: "?me mqtt4ssn:listensToTopic ?topic",
           TRANSLATOR: _IN_A_CHAT + "?channel a mqtt4ssn:Topic"},
    HTTP: {OBSERVER: f"{MINE} ?sensor td:hasForm ?form"},
    TELEGRAM: {TRANSLATOR: "?me telegram:hasBot ?bot"},
    EMAIL: {TRANSLATOR: _IN_A_CHAT + "?channel schema:email ?address"},
}

_DECLARED_Q = "SELECT DISTINCT ?kind WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind }"
_SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"

_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

_CLASS = "http://www.w3.org/2002/07/owl#Class"

#  EVERY AGENT THE WORLD STATES, where the same two graphs state them: whom a graph of an agent's
#  own may say it is.
_AGENTS_Q = "SELECT DISTINCT ?a WHERE { ?a a orexis:Agent }"

#  EVERY SELF THE STORE HOLDS, in any graph at all — COUNTED, never picked: a self in a graph the
#  boot did not put in is a self all the same to a text that asks for one.
_SELVES_Q = "SELECT DISTINCT ?self WHERE { GRAPH ?g { ?self a orexis:Self } } ORDER BY ?self"

_CLOSE_U = """
INSERT {{ GRAPH <{closure}> {{ ?a rdfs:subClassOf ?c }} }}
{using}
WHERE  {{ ?a rdfs:subClassOf+ ?c FILTER(isIRI(?a) && isIRI(?c) && ?a != ?c) }}"""

def documents(world: Path, packages=None, agent: str | None = None) -> list[Path]:
    """What a boot reads: the kernel's T-Box first, then the documents of `packages` — every
    package of the tree where none are named, which is what the operator's tools read — then every document in the
    world's directory, in `agent`'s own directory under its `secrets/` — every agent's, where none is named, as
    the operator's tools read the whole world — and under its `beliefs/`. Found by looking, never listed, and never
    a test's.

    A DOCUMENT IN AN AGENT'S OWN `secrets/<agent>/` IS READ LIKE ONE BESIDE THE WORLD, by that agent alone: what
    the world keeps out of the repository — where its place is, a chat's id — is still the world's, an agent
    without it boots, and no agent reads another's.

    `beliefs/` IS WHERE A WORLD KEEPS ITS AGENTS' OWN DOCUMENTS, and the name is for eyes: every
    document there is read, and whose each graph is, is what the graph says (`store.whose`). A
    world of several agents states each one's desires apart, because the derivation mints a want
    under every desire a store holds — kept by content, a bidder's desire stands in its own store
    and not its host's, whatever the file is called."""
    def under(directory: Path) -> list[Path]:
        return sorted(p for p in directory.glob("*") if p.is_file() and p.suffix in DOCUMENTS)
    world = Path(world)
    packages = every_package() if packages is None else packages
    secrets = world / SECRETS
    private = ([secrets / agent] if agent else
               sorted(d for d in secrets.iterdir() if d.is_dir()) if secrets.is_dir() else [])
    return [KERNEL / "ontology.ttl", *_documents_of(packages), *under(world),
            *(p for d in private for p in under(d)), *under(world / BELIEFS)]

def _documents_of(packages) -> list[Path]:
    """Every document in the directories of `packages`, their tests' cases apart."""
    return [p for package in packages for p in sorted(directory_of(package).rglob("*"))
            if p.suffix in DOCUMENTS and "tests" not in p.relative_to(directory_of(package)).parts]

@cache
def every_package() -> tuple[str, ...]:
    """Every package of the tree — each crate of `crates/` beside the kernel holding an
    `ontology.ttl` — in the order a pass runs their parts (`PASS`), and any
    package that order does not name after, by its name. Found by looking, never listed."""
    found = {package for d in TREE.iterdir() if (d / VOCABULARY).is_file() and (package := package_of(d.name))}
    return tuple(sorted(found, key=lambda package: (PASS.index(package) if package in PASS else len(PASS), package)))

@cache
def _declared_kinds() -> frozenset[str]:
    """Every class a package's ontology declares, read apart, as `_vocabularies` reads the roles."""
    return frozenset(q.subject.value for package in every_package()
                     for q in document(directory_of(package) / VOCABULARY).quads_for_pattern(
                         None, ox.NamedNode(_TYPE), ox.NamedNode(_CLASS), None)
                     if isinstance(q.subject, ox.NamedNode))

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
        doc = document(directory_of(package) / VOCABULARY)
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
    """Every role class the self of `store` plays: the class of each role its self graph says it
    `orexis:plays`, and every class those are beneath, that is beneath `orexis:Role` — read off the
    self graph alone, as a stance is, since a role is the agent's word about itself and nothing a
    peer or the world may say of it. Empty where it plays none."""
    _, steps = _vocabularies()
    stated = {r["kind"] for r in rows(store, _DECLARED_Q, graphs_of(store, SELF_GRAPH))}
    reached = set().union(*(_beneath(kind, steps, store) for kind in stated)) if stated else set()
    return frozenset(c for c in reached if c != ROLE and ROLE in _beneath(c, steps, store))

def packages_of(store: ox.Store) -> tuple[str, ...]:
    """Every package the self of `store` loads, in the order a pass runs their parts: each package
    whose ontology declares the class of a role the self plays (`roles_of`), and each transport a
    loaded role needs bytes from (`TRANSPORTS`), asked over the world's common graphs and the self.
    Nothing where the self plays no role — no default and no fixed mind
    (a-package-is-loaded-only-for-a-role-the-agent-is-declared-in)."""
    roles = roles_of(store)
    serving, _ = _vocabularies()
    loaded = {package for role, package in serving.items() if role in roles}
    known = [*graphs_of(store, BELIEF, common=True), *graphs_of(store, SELF_GRAPH)]
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

def _close_vocabulary(store: ox.Store) -> None:
    """Every `rdfs:subClassOf` step the ontology graphs reach, into the closure graph, so that
    one step is every step (one-graph-both-engines-read) and `closed` walks no path. Asked over
    every ontology graph at once, since a world's class may sit beneath a package's."""
    vocabularies = graphs_of(store, ONTOLOGY)
    using = "\n".join(f"USING <{g}>" for g in vocabularies)
    forget_graph(store, CLOSURE_GRAPH)
    update(store, _CLOSE_U.format(closure=CLOSURE_GRAPH, using=using))
    classify(store, CLOSURE_GRAPH, ONTOLOGY, DERIVED)

def _put_documents(store: ox.Store, world: Path, others: frozenset[str] = frozenset()) -> None:
    """Read every document of the tree and the world and put in the vocabulary, closed, and every common graph. Every
    graph of an agent's own is left out and still held to naming an agent of the world, so a world whose documents a
    tool reads whole is refused where an agent's boot would be.

    THE VOCABULARY FIRST, since whether a graph is read at all is the vocabulary's to say: a graph whose kind it does
    not declare is passed over (a-documents-kind-says-who-reads-it), quietly only for a kind in `others` or one a
    package declares, and said in the log otherwise."""
    own, passed = _put(store, world, read_with_imports(documents(world)), [])
    _owned(store, own)
    for path, _doc, graph, kinds in passed:
        expected = others & set(kinds) or (TREE in Path(path).resolve().parents and set(kinds) & _declared_kinds())
        log.log(logging.DEBUG if expected else logging.INFO,
                "passed over %s: %s is no kind this agent reads", graph, ", ".join(sorted(kinds)))


def _owned(store: ox.Store, own) -> list[tuple[ox.Store, str, str]]:
    """Each graph of an agent's own in `own`, (document, graph), with whose its document says it
    is (`store.whose`) — refused where that is the name of no agent the world states: a graph kept
    by an owner nobody is would be in no agent's store, silently."""
    agents = {r["a"] for r in rows(store, _AGENTS_Q, graphs_of(store, SOCIETY, WORLD))}
    out = []
    for doc, graph in own:
        owner = whose(doc, graph)
        if owner not in agents:
            raise DocumentRefused(f"{graph} says it is {owner}'s, and the world states no such agent")
        out.append((doc, graph, owner))
    return out

def _put(store: ox.Store, world: Path, read, passed) -> tuple[list, list]:
    """Put the vocabulary `read` holds and close it, then every graph of `read`, and of what was
    `passed` over before, whose kind the vocabulary now declares and that is common: every graph
    of a document outside the world's directory — a package's, a domain's — and every graph of the
    world's that says no owner, shared by every agent of the world, whatever its kind. What it says,
    never a kind: a world's graph saying whose it is is that agent's own (#953). The world's graphs of an agent's
    own as (document, graph), and what is passed over still as (path, document, graph, kinds)."""
    vocabulary = {path for path, doc in read if any(ONTOLOGY in k for k in kinds_in(doc).values())}
    for path, doc in read:
        if path in vocabulary:
            put_document(store, doc)
    _close_vocabulary(store)
    candidates = [(path, doc, graph, kinds) for path, doc in read if path not in vocabulary
                  for graph, kinds in kinds_in(doc).items()]
    common, own, still = [], [], []
    for path, doc, graph, kinds in [*passed, *candidates]:
        if not known(store, kinds):
            still.append((path, doc, graph, kinds))
            continue
        if world not in path.parents or whose(doc, graph) is None:
            common.append((doc, graph))
        else:
            own.append((doc, graph))
    for doc, graph in common:
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
    _put_documents(store, Path(world).resolve(), others=frozenset(others))
    close_catalogue(store)
    return store

def selves(store: ox.Store) -> list[str]:
    """Every agent the store says is the self, in any graph, sorted — one in an agent's store, none
    in a store holding a whole world, and anything else a store no boot will run."""
    return [r["self"] for r in rows(store, _SELVES_Q)]


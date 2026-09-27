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
process is told — then the world's other graphs, the agent's own, owned by it. The
catalogue is closed and the Planner's `scope` writes the scopes.

**A PACKAGE IS LOADED WHERE THE WORLD NEEDS IT (#824).** Belief, planning and execution are the
mind and every agent has them. Every other package — sensing, prediction, speech, the MQTT
transport — has its documents read and its modules imported only where its PREMISE holds: an
ASK in `PREMISES`, read off the world's public graphs with `$me` the agent. So the boot reads
the kernel, the mind and the world first, finds who the agent is, asks each premise, and only
then reads the documents of the packages whose premise held — closing the vocabulary again, and
taking a second look at any graph of the world passed over for a kind only such a package
declares. A premise is stated here, in the words of whoever CALLS the package, and not in the
package: speech's is in the transport's words and in execution's, the layer above it, whose words
speech may not speak; and what a premise decides is an `import` this file makes. Hanoi's mover
loads the mind and nothing else.

**A VOLUME LIVED IN** — a store that already holds a catalogue — forgets every graph a document
put in and nobody owns, and the closure, and reads the documents again: the kernel's, the
packages' and the world's public ones are asserted and replaced at every boot, which is how an
updated ontology reaches a running agent, and the premises are asked again, so a world that
stops needing a package stops loading it. The agent's own are left as they are, because they
are its beliefs from the first boot on (an-amendment-endows-what-it-grants).

**A PASS PLANS, THEN WALKS WHAT IS DUE.** `Runtime.run` calls the planner's pass, which derives
the wants, searches each and hands the plans to the executor; then ticks and drains the
executor until nothing is due, which for a fictive action is the whole plan and for a real one
is up to the first landing the world has not answered. **IT STOPS WHEN NO DESIRE IS HELD AND
EVERY WANT IS REACHED.** A desire is universal and never ends, so an agent holding one runs for
good; a want is one-shot and the pass withdraws it once met, so Hanoi's mover, holding one want
and no desire, solves its tower and exits. Wants standing with nothing walking is one of two
things: the budget cut the search short, which a plan's `planning:Exhausted` says and the next
pass continues, or nothing this agent holds reaches the want, which such an agent exits as
UNREACHABLE rather than looping on. Nothing here is threaded: the executor's two doors are called in turn on this thread, and a
pass that moved nothing sleeps the poll before the next.

**A SENSED WORLD RUNS THROUGH ITS TRANSPORT.** Where a sensor is reached over one, the member is
brought up and handed `deliver`; each pass drains what it queued — sensing writes, the rules
conclude sides, prediction writes the stretches ahead — before the planner's pass, and a step
whose action's implementation holds an `execution:Command` is taken by sending what it answers.

**A PEER IS TOLD, AND HEARD, THROUGH THE SAME TRANSPORT.** A step whose action's implementation
holds an `execution:Saying` makes documents of the present; the agent believes what it said, the rules
conclude of it at once, and each is sent to the agents it is to. A document a peer says arrives
on the topic the agent listens to and is believed by speech's `heard`, then revised like a reading.
"""

from __future__ import annotations

import argparse
import logging
import queue
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import pyoxigraph as ox

from agent import clock
from agent.belief.deliberator import Deliberator
from agent.execution.command import command
from agent.execution.executor import Executor
from agent.execution.implementation import COMMAND, SAYING, operations
from agent.execution.says import says
from agent.series import Series
from agent.ontology import CATALOGUE_GRAPH, CLOSURE_GRAPH, OREXIS, STATE, local_of
from agent.planning.planner import Planner
from agent.store import (answer, catalogue_of, classify, close_catalogue, closed, document, forget_graph, graphs_of, imports_of,
                         kinds_in, put_document, revisions_of, rows, update)

log = logging.getLogger("runtime")

KERNEL = Path(__file__).resolve().parent
ASSERTED = OREXIS + "Asserted"
DERIVED = OREXIS + "Derived"
ONTOLOGY = OREXIS + "OntologyGraph"
WORLD = OREXIS + "WorldGraph"
SOCIETY = OREXIS + "SocietyGraph"
PUBLIC = OREXIS + "PublicGraph"
GRAPH = OREXIS + "Graph"

MET, UNREACHABLE, UNFINISHED = "met", "unreachable", "unfinished"

DOCUMENTS = (".ttl", ".trig")
BELIEFS = "beliefs"

#  THE MIND: belief, planning and execution, which every agent has, since the container builds the
#  mind whatever the world (a-layer-is-a-package-and-need-loads-it). A package is named by its
#  directory under `agent/`, which is what rule 2 says a package is.
MIND = ("belief", "planning", "execution")
SENSING, PREDICTION, SPEECH, MQTT = "sensing", "prediction", "speech", "transport/mqtt"

#  A SENSOR OF THE AGENT'S: hosted by what it acts for, or by a sample of it — the one relation
#  sensing's callers read a sensor as the agent's by (the MQTT driver's `open` and `handle`).
_MINE = "$me orexis:actsFor ?subject . ?sensor sosa:isHostedBy/(sosa:isSampleOf)? ?subject ."

#  EVERY OTHER PACKAGE, AND WHAT IN THE WORLD MAKES THE AGENT NEED IT: an ASK over the world's
#  public graphs, `$me` the agent, which is each package's callers' reads answered in advance.
#  - SENSING, where a sensor is the agent's: `received` is called for such a sensor's message and
#    `missed` asks after its readings, and nothing else writes the observations its rules read;
#  - PREDICTION, where a sensor is the agent's AND a drift is declared: `predict` is asked of a
#    sensor that has just reported, and moves a reading only by a drift — the record's table said a
#    drift alone, and a market agent in a world importing climate would have loaded it for nothing;
#  - SPEECH, where the agent listens to a topic — a peer's document arrives there for `heard` — or
#    an action holds an `execution:Saying`, whose documents `said` believes when a step is taken.
#    Speech reads nothing of the world itself, so its premise is its callers' and in their words;
#  - THE MQTT TRANSPORT, where the agent listens to a topic or a sensor of its publishes on one —
#    `_transport_of` as it was, narrowed from any sensor in the world to the agent's own, which is
#    what the member subscribes to. Where the agent commands an actuator and neither holds, no
#    member is loaded: which actuators are the agent's is a domain's word, and no world has one.
#  Every word here is a T-Box term and the world's things are variables, so a premise names no
#  instance (rule 1); a new package under `agent/` loads nowhere until it is listed here or in
#  MIND, which `agent/tests/test_premises.py` holds the tree to.
PREMISES = {
    SENSING: f"ASK {{ {_MINE} }}",
    PREDICTION: f"ASK {{ {_MINE} ?drift a prediction:Drift }}",
    SPEECH: """ASK { { $me mqtt4ssn:listensToTopic ?topic }
                     UNION { ?action execution:implementation/execution:operation ?op . ?op a execution:Saying } }""",
    MQTT: f"""ASK {{ {{ $me mqtt4ssn:listensToTopic ?topic }}
                     UNION {{ {_MINE} ?sensor mqtt4ssn:observesTopic ?topic }} }}""",
}
EVERY = (*MIND, *PREMISES)

#  WHO THIS PROCESS IS: the AGENT with the id it was told. The id alone is not enough — the
#  sensing world's fern and the agent acting for it share one — so the kind is asked too. Asked
#  of the society graph, where a world with a bus states its principals, and of the world graph,
#  where a world with none states its one agent beside what it acts on.
_ME_Q = "SELECT ?me WHERE { ?me a orexis:Agent ; orexis:localId $id }"
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


def documents(world: Path, agent_id: str | None = None, packages=EVERY) -> list[Path]:
    """What a boot reads: the kernel's T-Box first, then the documents of `packages` — every
    package by default, which is what the operator's tools read — then every document in the
    world's directory, then the agent's own under `beliefs/`, named for its id. Found by looking,
    never listed, and never a test's.

    AN AGENT'S OWN FILE IS ITS OWN AND NOBODY ELSE'S. A world of several agents states each one's
    desires apart, because the derivation mints a want under every desire a store holds: read by
    all of them, a bidder's desire would stand in its host's store as well."""
    own = sorted(p for p in Path(world).iterdir() if p.is_file() and p.suffix in DOCUMENTS)
    mine = sorted(p for p in (Path(world) / BELIEFS).glob(f"{agent_id}.*") if p.suffix in DOCUMENTS) if agent_id else []
    return [KERNEL / "ontology.ttl", *_documents_of(packages), *own, *mine]


def _documents_of(packages) -> list[Path]:
    """Every document in the directories of `packages`, their tests' cases apart."""
    return [p for package in packages for p in sorted((KERNEL / package).rglob("*"))
            if p.suffix in DOCUMENTS and "tests" not in p.relative_to(KERNEL / package).parts]


def packages_of(store: ox.Store, me: str) -> tuple[str, ...]:
    """Every package the agent `me` loads, read off the world `store` holds: the mind, and each
    whose premise holds over the world's public graphs, in `PREMISES`' order."""
    public = graphs_of(store, PUBLIC)
    return (*MIND, *(package for package, premise in PREMISES.items()
                     if answer(store, premise, public, me=me)["boolean"]))


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


def _put_public(store: ox.Store, world: Path, agent_id: str | None = None) -> list[tuple[ox.Store, str]]:
    """Read the documents and put in the vocabulary, closed, and every public graph; answer the
    world's other graphs — the agent's own — as (document, graph), for the caller to put or not.

    THE VOCABULARY FIRST, since whether a graph is public is the vocabulary's to say — and so is
    whether it is read at all. A graph whose kind the vocabulary does not declare is passed over:
    a document of a kind another reader reads, onboarding's hardware, is not this agent's to hold,
    and what keeps it out is that nothing it loads says what the kind is
    (a-documents-kind-says-who-reads-it). A misspelled kind is passed over the same way, which is
    why onboarding, knowing every reader's vocabulary, refuses a world that holds one.

    THE MIND FIRST, AND A PACKAGE WHERE ITS PREMISE HOLDS. For an agent, the kernel, the mind and
    the world go in first, and the premises are asked of what that put in — the world's public
    graphs, which are the kernel's and the mind's kinds, so no premise waits on the package it
    decides. The documents of the packages whose premise held go in next, and a world graph passed
    over for a kind only such a package declares is looked at again. With no agent, every package
    is read at once: the operator's tools read every reader's vocabulary."""
    read = read_with_imports(documents(world, agent_id, MIND if agent_id else EVERY))
    own, passed = _put(store, world, read, [])
    if agent_id:
        close_catalogue(store)          # the rows say every kind they are beneath, so a premise reads the public graphs
        loaded = packages_of(store, _identity(store, agent_id))
        seen = {path for path, _ in read}
        more = [(path, doc) for path, doc in read_with_imports(_documents_of(p for p in loaded if p not in MIND))
                if path not in seen]
        if more:
            also, passed = _put(store, world, more, passed)
            own += also
        log.info("%s loads %s", agent_id, ", ".join(loaded))
    for _path, _doc, graph, kinds in passed:
        log.info("passed over %s: %s is no kind this agent reads", graph, ", ".join(sorted(kinds)))
    return own


def _put(store: ox.Store, world: Path, read, passed) -> tuple[list, list]:
    """Put the vocabulary `read` holds and close it, then every public graph of `read`, and of
    what was `passed` over before, whose kind the vocabulary now declares. The agent's own graphs
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
            public.append((doc, graph))
        else:
            own.append((doc, graph))
    for doc, graph in public:
        put_document(store, doc, graphs={graph})
    return own, still


def world_of(world: Path) -> ox.Store:
    """What a world says publicly, read as a boot reads it and closed, with no agent in it — what
    the simulator reads, and what the operator's tools read before the kinds they read and no
    agent does: its agents, its devices, its topics — and never where its broker listens, which
    is a deployment graph, a kind only onboarding reads. With no agent there is no premise to
    ask, so every package's documents are read: this is every reader's world, not one agent's."""
    store = ox.Store()
    update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph , orexis:Graph }} }}")
    _put_public(store, Path(world).resolve())
    close_catalogue(store)
    return store


def boot(world: Path, agent_id: str, store: ox.Store | None = None) -> ox.Store:
    """The agent's store from the documents: every graph classified by the document that holds
    it, the vocabulary closed, the catalogue closed, the scopes written. Handed a store that
    already holds a catalogue, read again every graph nobody owns and leave the agent's own."""
    world = Path(world).resolve()
    store = store if store is not None else ox.Store()
    lived_in = catalogue_of(store) is not None
    if lived_in:
        _forget_the_files(store)
    else:
        update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph , orexis:Graph }} }}")
    own = _put_public(store, world, agent_id)
    me = _identity(store, agent_id)
    if not lived_in:
        for doc, graph in own:
            put_document(store, doc, owner=me, graphs={graph})
    close_catalogue(store)
    Planner.scope(store)
    log.info("%s booted from %s%s", agent_id, world, " (a volume lived in: its own graphs kept)" if lived_in else "")
    return store


def _identity(store: ox.Store, agent_id: str) -> str:
    found = rows(store, _ME_Q, graphs_of(store, SOCIETY, WORLD), id=ox.Literal(agent_id))   # a str binds as an IRI; the id is a literal
    if len(found) != 1:
        raise RuntimeError(f"the world says {'nobody' if not found else 'several agents'} is {agent_id!r}")
    return found[0]["me"]


class Runtime:
    """One agent's process: what arrives sensed and revised, then the planner and the executor
    over one store, run pass by pass.

    A SENSED WORLD'S TRANSPORT is handed in brought up, or brought up here from the environment
    by `connect` — a `Transport` member's class, whose `connect` is handed `deliver`. A message
    arrives on the member's thread and is queued; the pass drains the queue on this one: sensing
    writes the observation, the rules conclude its side, prediction writes the stretches ahead and
    the rules conclude theirs, and the readings fallen due are asked for again. A step whose
    action's implementation holds an `execution:Command` is taken by sending what it answers, sized from
    the present, through the transport; a world with no transport takes steps as the executor
    does alone."""

    def __init__(self, beliefs: ox.Store, agent_id: str, *, budget: int | None = None,
                 intentions: ox.Store | None = None, transport=None, connect=None, series=None):
        self.beliefs, self.id = beliefs, agent_id
        self.series = series
        self.me = _identity(beliefs, agent_id)
        self.packages = packages_of(beliefs, self.me)
        self._missed, self._predict, self._said = _imported(self.packages)
        self.inbox: queue.SimpleQueue = queue.SimpleQueue()
        self.transport = transport if transport is not None else (
            connect.connect(self.me, self.deliver) if connect is not None else None)
        self.executor = Executor(beliefs, agent_id, intentions,
                                 take=self._take if self.transport is not None else None)
        self.planner = Planner(beliefs, agent_id, executor=self.executor, **({"budget": budget} if budget else {}))
        self.deliberator = Deliberator(beliefs, agent_id)
        #  A STEP KEPT BELOW, AND THE WORLD THE EXECUTOR MOVES: before a step is taken the Planner
        #  says whether a rule keeps it one level down, and what the executor writes as the world
        #  is revised, so a fact the rules conclude of it — what a disk is on — moves with it.
        self.executor.refine = self.planner.refine
        self.executor.on_write = lambda graph: self._revise([graph], clock.now())
        #  AND WHAT THE WORLD AUTHORED: its state, revised once, so a fact concluded from where
        #  things stand is believed from the first pass and not only after something moves.
        self._revise([g for g in graphs_of(beliefs, STATE) if not revisions_of(beliefs, g)], clock.now())
        if self.transport is not None:
            self.transport.open(beliefs)

    def deliver(self, channel: str, payload: bytes, at) -> None:
        """What a transport's thread hands on: queued, for the pass to take on this thread."""
        self.inbox.put((channel, payload, at))

    def sense(self, now) -> list[str]:
        """Take every message queued since the last pass: a peer's document believed and revised,
        a reading written by sensing, revised, and predicted from; then ask again for every
        reading fallen due. The graphs written.

        EACH GRAPH IS REVISED BESIDE PUBLIC KNOWLEDGE ALONE. Every rule shipped reads one graph
        and what the world states — a reading and its subject's ranges, a round and nothing
        else — and a revision is replaced only when its own source is written again. Revised
        beside everything believed, the first of two readings arriving together took the
        second's side into its own revision, where the second's next reading never reached it:
        a soil read inside stayed below in the thermometer's revision."""
        written, sensors = [], []
        while self.transport is not None:
            try:
                channel, payload, at = self.inbox.get_nowait()
            except queue.Empty:
                break
            for sensor, graph in self.transport.handle(self.beliefs, channel, payload, at):
                written.append(graph)
                if sensor is None:
                    continue                                    # a peer's document
                sensors.append(sensor)
                if self.series is not None:
                    self.series.record(self.beliefs, graph)     # what a person watches
        if not written:
            return []
        self._revise(written, now)
        predicted = [graph for sensor in dict.fromkeys(sensors)
                     for graph in self._predict(self.beliefs, self.me, sensor, now=now)] if self._predict else []
        self._revise(predicted, now)
        for sensor in (self._missed(self.beliefs, self.me, now) if self._missed else []):
            self.transport.sense_now(self.beliefs, sensor)
        return written + predicted

    def _revise(self, graphs: list[str], now) -> None:
        """What the rules conclude of each graph written, beside what the world states and
        nothing else, at once."""
        if not graphs:
            return
        public = graphs_of(self.beliefs, PUBLIC)
        for graph in graphs:
            self.deliberator.changed(graph, read=public)
        self.deliberator.deliberate(now)

    def _take(self, said: dict, intention: str) -> None:
        """Take a step by its action's implementation, order by order: every command of an order
        sent, sized from the present, and every saying's documents believed as said, revised
        and sent to every agent they are to — so a later order is made from the present the
        earlier ones left. A step whose action has no operation is said in the log, as the
        executor would."""
        orders = sorted({op.order for op in operations(self.beliefs, said.get("fills") or "")
                         if op.kind in (COMMAND, SAYING)})
        if not orders:
            self.executor.say(said, intention)
            return
        for order in orders:
            for actuator, payload in command(self.beliefs, said, self.me, order=order):
                self.transport.actuate(self.beliefs, actuator, payload)
            written = []
            for agents, doc in says(self.beliefs, said, self.me, order=order):
                written += self._said(self.beliefs, self.me, doc)      # a Saying is speech's premise
                payload = doc.dump(format=ox.RdfFormat.TRIG)
                for agent in agents:
                    self.transport.tell(self.beliefs, agent, payload)
            self._revise(written, clock.now())

    def run(self, *, passes: int | None = None, poll_s: float = 1.0) -> str:
        """Pass after pass until nothing is left to pursue (`met`), or nothing this agent holds
        reaches a want that stands (`unreachable`), or `passes` ran out (`unfinished`).

        A DESIRE NEVER ENDS AND A WANT DOES. A desire is universal — it asks that something hold
        whenever it is asked — so an agent holding one runs for as long as the process does, and
        a pass with nothing to do waits the poll for the world to move. A want is one-shot and is
        withdrawn once reached, so an agent holding wants and no desire, Hanoi's mover, exits
        when every want is reached and nothing walks. Unreachable is an exit only for such an
        agent: one holding a desire keeps watching, since the world may yet open a way. An agent a
        transport reaches runs for good too, desire or not: what it senses goes on arriving."""
        n = 0
        while passes is None or n < passes:
            n += 1
            now = clock.now()
            self.sense(now)
            self.planner.plan(now)
            standing, walking = self.planner.standing(now), self.executor.walking()
            #  WHAT KEEPS AN AGENT RUNNING: a desire, which asks at every instant, or a transport,
            #  since an agent that senses has readings to keep writing whether or not it wants
            #  anything of them — the terrace watches and pursues nothing.
            lasting = self.transport is not None or self.planner.holds_a_desire()
            if not standing and not walking:
                if not lasting:
                    log.info("%s: every want is reached and no desire is held, after %d pass(es)", self.id, n)
                    return MET
                time.sleep(poll_s)
                continue
            if not walking:
                if self.planner.exhausted():
                    continue                    # the budget cut a search short; the next pass continues it
                log.error("%s: %d want(s) stand and nothing this agent holds reaches them: %s",
                          self.id, len(standing), ", ".join(local_of(w) for w in standing))
                if not lasting:
                    return UNREACHABLE
                time.sleep(poll_s)
                continue
            if not self._walk(now):
                time.sleep(poll_s)
        return UNFINISHED


    def _walk(self, now) -> int:
        """Tick and drain until nothing more happens at this instant: how many steps were taken.
        One tick hands the due heads over and holds the taken ones to what they predicted, and a
        head moved along in one tick is handed over only by the next, so the walk ends on two
        ticks in a row that hand nothing over."""
        taken, idle = 0, 0
        while idle < 2:
            if self.executor.tick(now):
                taken += self.executor.drain()
                idle = 0
            else:
                idle += 1
            now = clock.now()
        return taken


def _imported(packages):
    """What the runtime calls of a package beyond the mind — sensing's `missed`, prediction's
    `predict`, speech's `said` — imported here, where the package is loaded, and None where it is
    not. The only place the runtime imports them, so a world whose premise does not hold never
    loads their modules; the layout tests see these imports as they see any other."""
    missed = predict = said = None
    if SENSING in packages:
        from agent.sensing.missed import missed
    if PREDICTION in packages:
        from agent.prediction.predict import predict
    if SPEECH in packages:
        from agent.speech.said import said
    return missed, predict, said


def _transport_of(beliefs: ox.Store, me: str):
    """The transport member the agent is loaded with, or None where no member's premise holds —
    and then the member's module is never imported. MQTT is the one member that ships; its
    library is imported by its own `connect`, so even a world that loads it is not handed paho
    until it connects."""
    if MQTT not in packages_of(beliefs, me):
        return None
    from agent.transport.mqtt.driver import Mqtt
    return Mqtt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One agent of Agent 0.2.0, booted from a world's files and run until nothing is left to pursue.")
    parser.add_argument("world", type=Path, help="the world's directory")
    parser.add_argument("agent", help="this agent's id — the one identifier a process is told")
    parser.add_argument("--volume", type=Path, help="where the store persists; in memory when absent")
    parser.add_argument("--budget", type=int, help="candidates a search may weigh per pass; the Planner's own where absent")
    parser.add_argument("--passes", type=int, help="stop after this many passes whatever stands")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    store = ox.Store(str(args.volume)) if args.volume else None
    beliefs = boot(args.world, args.agent, store)
    outcome = Runtime(beliefs, args.agent, budget=args.budget, connect=_transport_of(beliefs, _identity(beliefs, args.agent)),
                      series=Series.from_environment()).run(passes=args.passes)
    return {MET: 0, UNREACHABLE: 1, UNFINISHED: 2}[outcome]


if __name__ == "__main__":
    sys.exit(main())

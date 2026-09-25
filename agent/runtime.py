"""The runtime of Agent 0.2.0: one process, one agent, one world — booted from the world's files
and run, pass by pass, until nothing is left to pursue.

**A WORLD IS A DIRECTORY OF DOCUMENTS, AND EACH SAYS WHAT IT IS.** `boot` reads every document
the kernel ships — its T-Box (`agent/ontology.ttl`), every package's ontology and rule set — and
every `.ttl` and `.trig` file in the world's directory, whatever it is called. A Turtle file is
one graph named by its own IRI, and `<> a orexis:DesireGraph` in it says what that graph is; a
TriG file names its graphs and states their kinds in its default graph. `store.document` reads
either, and `store.put_document` puts the graphs in and moves the rows about them into the
catalogue, where every reader asks; a document stating no kind, or claiming to be the
catalogue, is refused. The vocabulary goes first, since what a graph is depends on it: every
document that says it is an `orexis:OntologyGraph`, then the closure over `rdfs:subClassOf`,
written into a graph of its own and derived, so that a kind is every kind it is beneath. Then
the world's public graphs, then who the agent is — off the world graph, by the one identifier
the process is told — then the world's other graphs, the agent's own, owned by it. The
catalogue is closed and the Planner's `scope` writes the scopes.

**A VOLUME LIVED IN** — a store that already holds a catalogue — forgets every graph a document
put in and nobody owns, and the closure, and reads the documents again: the kernel's, the
packages' and the world's public ones are asserted and replaced at every boot, which is how an
updated ontology reaches a running agent. The agent's own are left as they are, because they
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
whose action carries `execution:command` is taken by sending what the command answers.
"""

from __future__ import annotations

import argparse
import logging
import os
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
from agent.prediction.predict import predict
from agent.sensing.missed import missed
from agent.signing import load_key, sign
from agent.ontology import CATALOGUE_GRAPH, CLOSURE_GRAPH, OREXIS, local_of
from agent.planning.planner import Planner
from agent.store import (catalogue_of, classify, close_catalogue, closed, document, forget_graph, graphs_of, imports_of, kinds_in,
                         put_document, rows, update)

log = logging.getLogger("runtime")

KERNEL = Path(__file__).resolve().parent
ASSERTED = OREXIS + "Asserted"
DERIVED = OREXIS + "Derived"
ONTOLOGY = OREXIS + "OntologyGraph"
WORLD = OREXIS + "WorldGraph"
PUBLIC = OREXIS + "PublicGraph"
DESIRES = OREXIS + "DesireGraph"

MET, UNREACHABLE, UNFINISHED = "met", "unreachable", "unfinished"

DOCUMENTS = (".ttl", ".trig")

_ME_Q = "SELECT ?me WHERE { ?me orexis:localId $id }"
_DESIRES_Q = "SELECT ?d WHERE { ?d a orexis:Desire } LIMIT 1"
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


def documents(world: Path) -> list[Path]:
    """What a boot reads: the kernel's T-Box first, then every package's documents, then every
    document in the world's directory. Found by looking, never listed, and never a test's."""
    kernel = KERNEL / "ontology.ttl"
    packages = sorted(p for p in KERNEL.rglob("*") if p.suffix in DOCUMENTS and p != kernel
                      and "tests" not in p.relative_to(KERNEL).parts)
    own = sorted(p for p in Path(world).iterdir() if p.is_file() and p.suffix in DOCUMENTS)
    return [kernel, *packages, *own]


def _read_with_imports(paths: list[Path]) -> list[tuple[Path, ox.Store]]:
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
    read = _read_with_imports(documents(world))
    #  THE VOCABULARY FIRST, since whether a graph is public is the vocabulary's to say.
    vocabulary = {path for path, doc in read if any(ONTOLOGY in k for k in kinds_in(doc).values())}
    for path, doc in read:
        if path not in vocabulary:
            continue
        put_document(store, doc)
    _close_vocabulary(store)
    public, own = [], []
    for path, doc in read:
        if path in vocabulary:
            continue
        for graph, kinds in kinds_in(doc).items():
            beneath = {k for kind in kinds for k in closed(store, kind)}
            if world not in path.parents or PUBLIC in beneath:
                public.append((doc, graph))
            else:
                own.append((doc, graph))
    for doc, graph in public:
        put_document(store, doc, graphs={graph})
    me = _identity(store, agent_id)
    if not lived_in:
        for doc, graph in own:
            put_document(store, doc, owner=me, graphs={graph})
    close_catalogue(store)
    Planner.scope(store)
    log.info("%s booted from %s%s", agent_id, world, " (a volume lived in: its own graphs kept)" if lived_in else "")
    return store


def _identity(store: ox.Store, agent_id: str) -> str:
    found = rows(store, _ME_Q, graphs_of(store, WORLD), id=ox.Literal(agent_id))   # a str binds as an IRI; the id is a literal
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
    action carries `execution:command` is taken by sending what the command answers, sized from
    the present, through the transport; a world with no transport takes steps as the executor
    does alone."""

    def __init__(self, beliefs: ox.Store, agent_id: str, *, budget: int | None = None,
                 intentions: ox.Store | None = None, transport=None, connect=None, signing_key=None):
        self.beliefs, self.id = beliefs, agent_id
        self.signing_key = signing_key
        self.me = _identity(beliefs, agent_id)
        self.inbox: queue.SimpleQueue = queue.SimpleQueue()
        self.transport = transport if transport is not None else (
            connect.connect(self.me, self.deliver) if connect is not None else None)
        self.executor = Executor(beliefs, agent_id, intentions,
                                 take=self._take if self.transport is not None else None)
        self.planner = Planner(beliefs, agent_id, executor=self.executor, **({"budget": budget} if budget else {}))
        self.deliberator = Deliberator(beliefs, agent_id)
        if self.transport is not None:
            self.transport.open(beliefs)

    def deliver(self, channel: str, payload: bytes, at) -> None:
        """What a transport's thread hands on: queued, for the pass to take on this thread."""
        self.inbox.put((channel, payload, at))

    def sense(self, now) -> list[str]:
        """Take every message queued since the last pass: each written by sensing, revised, and
        predicted from; then ask again for every reading fallen due. The graphs written."""
        written, sensors = [], []
        while self.transport is not None:
            try:
                channel, payload, at = self.inbox.get_nowait()
            except queue.Empty:
                break
            for sensor, graph in self.transport.handle(self.beliefs, channel, payload, at):
                written.append(graph)
                sensors.append(sensor)
                self.deliberator.changed(graph)
        if not written:
            return []
        self.deliberator.deliberate(now)
        for sensor in dict.fromkeys(sensors):
            for graph in predict(self.beliefs, self.me, sensor, now=now):
                written.append(graph)
                self.deliberator.changed(graph)
        self.deliberator.deliberate(now)
        for sensor in missed(self.beliefs, self.me, now):
            self.transport.sense_now(self.beliefs, sensor)
        return written

    def _take(self, said: dict, intention: str) -> None:
        """Take a step by sending what its action's command answers, sized from the present and
        SIGNED with this agent's key, since a device opens only for its holder; a step whose action
        carries none is said in the log, as the executor would. With no key the command is not
        sent — a device would refuse it — and the executor's patience says what that costs."""
        sent = command(self.beliefs, said, self.me)
        if not sent:
            self.executor.say(said, intention)
            return
        if self.signing_key is None:
            log.error("%s: no signing key, so the command for %s is not sent", self.id, local_of(said["step"]))
            return
        for actuator, payload in sent:
            self.transport.actuate(self.beliefs, actuator, sign(payload, self.signing_key))

    def run(self, *, passes: int | None = None, poll_s: float = 1.0) -> str:
        """Pass after pass until nothing is left to pursue (`met`), or nothing this agent holds
        reaches a want that stands (`unreachable`), or `passes` ran out (`unfinished`).

        A DESIRE NEVER ENDS AND A WANT DOES. A desire is universal — it asks that something hold
        whenever it is asked — so an agent holding one runs for as long as the process does, and
        a pass with nothing to do waits the poll for the world to move. A want is one-shot and is
        withdrawn once reached, so an agent holding wants and no desire, Hanoi's mover, exits
        when every want is reached and nothing walks. Unreachable is an exit only for such an
        agent: one holding a desire keeps watching, since the world may yet open a way."""
        n = 0
        while passes is None or n < passes:
            n += 1
            now = clock.now()
            self.sense(now)
            self.planner.plan(now)
            standing, walking = self.planner.standing(now), self.executor.walking()
            lasting = self._holds_a_desire()
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

    def _holds_a_desire(self) -> bool:
        return bool(rows(self.beliefs, _DESIRES_Q, graphs_of(self.beliefs, DESIRES)))

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


def _transport_of(beliefs: ox.Store):
    """The transport member the world says the agent's sensors are reached through, or None for
    a world nothing is sensed in. MQTT is the one member that ships; its library is imported by
    its own `connect`, so a world with no sensors never loads it."""
    from agent.transport.mqtt.driver import Mqtt
    sensors = rows(beliefs, "SELECT ?s WHERE { ?s a sosa:Sensor }", graphs_of(beliefs, PUBLIC))
    return Mqtt if any(Mqtt.claims(beliefs, r["s"]) for r in sensors) else None


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
    #  THE AGENT'S OWN KEY, mounted into its container alone: where a deployment says it is.
    key = os.environ.get("OREXIS_SIGNING_KEY")
    outcome = Runtime(beliefs, args.agent, budget=args.budget, connect=_transport_of(beliefs),
                      signing_key=load_key(key) if key else None).run(passes=args.passes)
    return {MET: 0, UNREACHABLE: 1, UNFINISHED: 2}[outcome]


if __name__ == "__main__":
    sys.exit(main())

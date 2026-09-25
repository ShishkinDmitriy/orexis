"""The runtime of Agent 0.2.0: one process, one agent, one world — booted from the world's files
and run, pass by pass, until every desire is met.

**A WORLD IS A DIRECTORY OF FILES, AND A BOOT IS A READ OF THEM.** `boot` builds the agent's
store from `world/<name>/`: the vocabulary — the kernel's T-Box (`agent/ontology.ttl`), every
package's `ontology.ttl` and the world's own — into one ontology graph, closed over
`rdfs:subClassOf` so that a kind is every kind it is beneath; `world.ttl` as the world graph;
`actions.ttl` as the actions; `desires.ttl` as the graph of desires, the agent's; and `state.ttl`
as the first state graph, the agent's. Each graph is classified as it is created, the catalogue
is closed, and the Planner's `scope` writes the scopes. Who the agent is comes off the world graph by
the one identifier the process is told, its id. A store that already holds a catalogue is a
volume the agent has lived in: the public graphs are reloaded from the files, because they are
asserted and replaced at every boot, and the desires and the state are left as they are,
because they are the agent's (an-amendment-endows-what-it-grants).

**A PASS PLANS, THEN WALKS WHAT IS DUE.** `Runtime.run` calls the planner's pass, which derives
the wants, searches each and hands the plans to the executor; then ticks and drains the
executor until nothing is due, which for a fictive action is the whole plan and for a real one
is up to the first landing the world has not answered. **IT STOPS WHEN EVERY DESIRE IS MET**,
which is when no want stands and no intention walks after a pass — a desire met mints no want,
and a want met is withdrawn — so a world whose one want is one-shot, Hanoi, solves its tower and
exits. Wants standing with nothing walking is one of two things: the budget cut the search
short, which a plan's `planning:Exhausted` says and the next pass continues, or nothing this
agent holds reaches the want, which is UNREACHABLE and is exited saying so rather than looped
on. Nothing here is threaded: the executor's two doors are called in turn on this thread, and a
pass that moved nothing sleeps the poll before the next.

**NOT YET WIRED**, and named so: sensing, prediction, the belief package's deliberator and the
transport. Hanoi has none of them; they join the runtime with the first sensed world.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pyoxigraph as ox

from agent import clock
from agent.execution.executor import Executor
from agent.ontology import (ACTIONS_GRAPH, CATALOGUE_GRAPH, DESIRE_ASSERTED_GRAPH, ONTOLOGY_GRAPH, OREXIS,
                            STATE, STATE_GRAPH, WORLD_GRAPH, local_of)
from agent.planning.planner import Planner
from agent.store import catalogue_of, classify, close_catalogue, rows, update

log = logging.getLogger("runtime")

KERNEL = Path(__file__).resolve().parent
ASSERTED = OREXIS + "Asserted"
ONTOLOGY = OREXIS + "OntologyGraph"
WORLD = OREXIS + "WorldGraph"
PUBLIC = OREXIS + "PublicGraph"
DESIRES = OREXIS + "DesireGraph"

MET, UNREACHABLE, UNFINISHED = "met", "unreachable", "unfinished"

#  THE WORLD'S FILES, each to the graph it is, in the order a boot reads them.
VOCABULARY, WORLD_FILE, ACTIONS_FILE, DESIRES_FILE, STATE_FILE = "ontology.ttl", "world.ttl", "actions.ttl", "desires.ttl", "state.ttl"

_ME_Q = "SELECT ?me WHERE { GRAPH $world { ?me orexis:localId $id } }"
_CLOSE_U = """
INSERT { GRAPH $vocabulary { ?a rdfs:subClassOf ?c } }
WHERE  { GRAPH $vocabulary { ?a rdfs:subClassOf ?b . ?b rdfs:subClassOf ?c } FILTER(?a != ?c) }"""
_SIZE_Q = "SELECT (COUNT(*) AS ?n) WHERE { GRAPH $g { ?s ?p ?o } }"


def vocabularies(world: Path) -> list[Path]:
    """The vocabulary a boot loads: the kernel's T-Box first, then every package's, then the
    world's own where it has one. Found by looking, never listed."""
    packages = sorted(p for p in KERNEL.rglob("ontology.ttl") if p != KERNEL / VOCABULARY and "tests" not in p.parts)
    own = [world / VOCABULARY] if (world / VOCABULARY).is_file() else []
    return [KERNEL / VOCABULARY, *packages, *own]


def _load(store: ox.Store, graph: str, path: Path) -> None:
    store.load(path.read_bytes(), format=ox.RdfFormat.TURTLE, to_graph=ox.NamedNode(graph), base_iri=path.resolve().as_uri())


def _replace(store: ox.Store, graph: str, paths: list[Path]) -> None:
    store.remove_graph(ox.NamedNode(graph))
    for path in paths:
        _load(store, graph, path)


def _close_vocabulary(store: ox.Store, graph: str) -> None:
    """Materialise `rdfs:subClassOf` to a fixpoint in the vocabulary graph, so that one step is
    every step (one-graph-both-engines-read) and `closed` walks no path."""
    before = -1
    while True:
        (row,) = rows(store, _SIZE_Q, (), g=graph)
        if int(row["n"]) == before:
            return
        before = int(row["n"])
        update(store, _bind(_CLOSE_U, vocabulary=graph))


def _bind(text: str, **graphs: str) -> str:
    for token, graph in graphs.items():
        text = text.replace(f"${token}", f"<{graph}>")
    return text


def boot(world: Path, agent_id: str, store: ox.Store | None = None) -> ox.Store:
    """The agent's store from the world's files: every graph classified, the catalogue closed,
    the scopes written. Handed a store that already holds a catalogue, reload the public
    graphs and leave the agent's own."""
    world = Path(world)
    store = store if store is not None else ox.Store()
    for name in (WORLD_FILE, ACTIONS_FILE, DESIRES_FILE, STATE_FILE):
        if not (world / name).is_file():
            raise FileNotFoundError(f"{world} has no {name} — a 0.2.0 world is five files, and this one is missing that")
    lived_in = catalogue_of(store) is not None
    if not lived_in:
        update(store, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph , orexis:Graph }} }}")
    _replace(store, ONTOLOGY_GRAPH, vocabularies(world))
    _close_vocabulary(store, ONTOLOGY_GRAPH)
    if not lived_in:
        classify(store, ONTOLOGY_GRAPH, ONTOLOGY, ASSERTED)
    _replace(store, WORLD_GRAPH, [world / WORLD_FILE])
    me = _identity(store, agent_id)
    _replace(store, ACTIONS_GRAPH, [world / ACTIONS_FILE])
    if not lived_in:
        classify(store, WORLD_GRAPH, WORLD, ASSERTED)
        classify(store, ACTIONS_GRAPH, PUBLIC, ASSERTED)
        _load(store, DESIRE_ASSERTED_GRAPH, world / DESIRES_FILE)
        classify(store, DESIRE_ASSERTED_GRAPH, DESIRES, ASSERTED, me)
        _load(store, STATE_GRAPH, world / STATE_FILE)
        classify(store, STATE_GRAPH, STATE, ASSERTED, me)
    close_catalogue(store)
    Planner.scope(store)
    log.info("%s booted from %s%s", agent_id, world, " (a volume lived in: desires and state kept)" if lived_in else "")
    return store


def _identity(store: ox.Store, agent_id: str) -> str:
    found = rows(store, _ME_Q, (), world=WORLD_GRAPH, id=ox.Literal(agent_id))   # a str binds as an IRI; the id is a literal
    if len(found) != 1:
        raise RuntimeError(f"the world says {'nobody' if not found else 'several agents'} is {agent_id!r}")
    return found[0]["me"]


class Runtime:
    """One agent's process: the planner and the executor over one store, run pass by pass."""

    def __init__(self, beliefs: ox.Store, agent_id: str, *, budget: int | None = None, intentions: ox.Store | None = None):
        self.beliefs, self.id = beliefs, agent_id
        self.executor = Executor(beliefs, agent_id, intentions)
        self.planner = Planner(beliefs, agent_id, executor=self.executor, **({"budget": budget} if budget else {}))

    def run(self, *, passes: int | None = None, poll_s: float = 1.0) -> str:
        """Pass after pass until every desire is met (`met`), or nothing this agent holds
        reaches a want that stands (`unreachable`), or `passes` ran out (`unfinished`)."""
        n = 0
        while passes is None or n < passes:
            n += 1
            now = clock.now()
            self.planner.plan(now)
            standing, walking = self.planner.standing(now), self.executor.walking()
            if not standing and not walking:
                log.info("%s: every desire is met after %d pass(es)", self.id, n)
                return MET
            if not walking:
                if self.planner.exhausted():
                    continue                    # the budget cut a search short; the next pass continues it
                log.error("%s: %d want(s) stand and nothing this agent holds reaches them: %s",
                          self.id, len(standing), ", ".join(local_of(w) for w in standing))
                return UNREACHABLE
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One agent of Agent 0.2.0, booted from a world's files and run until every desire is met.")
    parser.add_argument("world", type=Path, help="the world's directory")
    parser.add_argument("agent", help="this agent's id — the one identifier a process is told")
    parser.add_argument("--volume", type=Path, help="where the store persists; in memory when absent")
    parser.add_argument("--budget", type=int, help="candidates a search may weigh per pass; the Planner's own where absent")
    parser.add_argument("--passes", type=int, help="stop after this many passes whatever stands")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    store = ox.Store(str(args.volume)) if args.volume else None
    outcome = Runtime(boot(args.world, args.agent, store), args.agent, budget=args.budget).run(passes=args.passes)
    return {MET: 0, UNREACHABLE: 1, UNFINISHED: 2}[outcome]


if __name__ == "__main__":
    sys.exit(main())

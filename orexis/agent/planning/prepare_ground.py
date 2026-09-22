"""Preparing the ground: what a search over one scope is given, and the world it stands in.

BOTH HALVES ARE IN THE NAME. What crosses from the belief base is copied in, and what the
agent can SEE — the present, and what each prediction makes of it — is laid out as one graph
per period. The second is the reason the first is worth doing: a store with the beliefs in it
and no grounds is a store where a desire asked at a future instant sees the reading AND the
prediction of it, which is the failure `_lay_ground` exists to close. It was called
`init_imaginarium`, which named the store rather than the work.

WHY THERE IS A SECOND STORE AT ALL. A plan is `(beliefs − retracts) + adds`, applied step
after step, and every step's rule is a SPARQL query. A query reads ONE store, so the question
"what would be true here" is answerable only if there is a store in which *here* is what is
true. There was not: the predecessor computed each step honestly and asked the BELIEF BASE for
the next one, so the first step was right and every step after it was predicted from the
reading on disk. Depth beyond 1 was nominal for any desire about a measured value, which is
most of them. So the rules are run against a second `pyoxigraph.Store`, in memory for the life
of one plan — the **imaginarium**, in the sovereign's word, and the word says the thing that
matters: what is in it never happened. See
knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md.

**IT IS A STORE**, and was a class twice over — a subclass of the store's wrapper, then a
holder forwarding twenty-two methods of which a search called five. The graphs a rule may read
are copied in, so an ordinary query means the same thing here as it does in the belief base:
`graphs_of(PUBLIC)` discovers the same names off the same ontology graph, and `effects.apply`
cannot tell the two apart. What differs is that this one was constructed with no path, so it
is memory and there is nothing to clean up — the whole store is dropped when the plan ends,
and a crash mid-plan leaves nothing behind to find. That is most of why it is a store of its
own rather than a graph in the agent's: a graph can be forgotten to be dropped, and a store
that was never on disk cannot be.

**AND IT IS THE CHEAP HALF**, measured on this bench, alternated within one session because
the Pi drifts about twofold between invocations. A whole pass over the plans case costs
13.9 ms with this store in memory and 32.6 ms with it on disk — 2.3x, filling included. Per
operation, medians of five rounds against a 5,000-quad store: forking a two-quad graph 0.12 ms
against 0.25, forking the 5,000 22.4 ms against 92.0, a SELECT 2.6 ms against 3.3, a DELETE
0.13 ms against 0.21. So a READ pays about a third more and a WRITE pays two to four times,
which is the shape RocksDB has: the engine answers questions at nearly the same speed either
way and pays for durability when something changes. A pass writes a graph per fork, so the
argument from cleanup and the argument from cost point the same way.

**AND IT DOES NOT EVEN SAVE MEMORY, which is the reason somebody would reach for a file.** An
imaginarium after a pass over the plans case is 97 quads in 11 named graphs, filled from an
86-quad belief base — a fork copies the READINGS, not the world, so the shared thousands cross
once and each node adds its own handful. Held on disk instead, peak RSS went UP: 50 MB against
57, because RocksDB's memtables, block cache and file handles cost more than 97 quads ever
could, and the directory was 270 KB. If what is wanted is to SEE a pass after it ends, dumping
the whole imaginarium as n-quads costs 0.09 ms and 17.6 KB and hands back a text anything can
read, where a store on disk is a directory one process at a time may open.

A FUNCTION OVER TWO STORES, which is the one thing in this package that cannot be a function
over a single one. `beliefs` is read and the empty store is written; both are the engine, a
`pyoxigraph.Store`, and the caller makes the empty one. Everything that happens to a possible
world afterwards happens to that store the ordinary way, so this is the seam and not a wrapper.

ITS OWN FILE because it is its own act. `imaginarium.py` holds the doors a rule is asked
through once a world exists; this decides what a world is made OF, which is a question about
the belief base rather than about the imaginarium — and the two shared a file only because the
fill used to be three lines inside a constructor.

--- AND THE GROUND WORLDS, which are the second half of filling one --------------------------

**A PREDICTION IS AN ACTION NOBODY TAKES.** What it makes true is its graph's own contents —
concrete, because a forecast is a value at an instant — and what it takes away is
`orexis:retracts` on its catalogue row, a `DELETE … WHERE` naming `GRAPH $state`, because what
is standing in that place is not something a forecast can name in advance. Its period says
WHEN it applies rather than a precondition saying whether it may. So the timeline is laid by
exactly the machinery the search walks: fork the period before, run the retraction against the
fork, add what the prediction holds.

WHY IT HAD TO BECOME A DIFF. A prediction used to be a STATE — a graph holding the reading it
foretold — and a door handed a reader every graph holding at an instant, so a met-test asked at
a foreseen instant saw the reading AND the prediction of it. A shape holds over EVERY value, so
the stale one still violated: measured, a tank low now and a forecast refilling it read *unmet
from twelve, lifts NEVER*, because the present's 5 outlived the forecast's 20. Nothing was
wrong with the forecast; there was no place in the pass where it REPLACED anything.

**AND THE PERIODS COLLAPSE.** Each ground is hashed as a possible world is, and where two
neighbouring periods reach the same facts the second is not a period at all: nothing a met-test
can read moved, so nothing it could answer differs there. Measured on three boundaries whose
middle prediction restated the present — three boundaries, two grounds. That is what bounds the
judging: a desire is asked once per DISTINCT ground rather than once per boundary, so a store
thick with forecasts that say nothing new costs a pass nothing.

**WHAT IS BUILT IS CLASSIFIED, NOT RETURNED.** Each ground is a graph with the stretch it holds
over, `planning:GroundGraph`, so a reader asks `graphs_of(store, GROUND_GRAPH, at=T)` and is
handed the one world standing then. A list handed back would be a second place the answer lived
(a-reader-states-the-kinds-it-reads).
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from orexis.agent.ontology import (BELIEF, DESIRE, OREXIS, PREDICTION, PUBLIC, RECORD,
                                             STATE, WANT)
from orexis.agent.hash_named_graph import hash_named_graph
from orexis.agent.store import (Raw, add_quads, bind, catalogue_of, classify, copy_graph,
                                          forget_graph, graphs_of, quads, rows, update)

from .apply_effects import apply_diff
from .ontology import GROUND_GRAPH

_PROV = "http://www.w3.org/ns/prov#"

log = logging.getLogger("prepare_ground")


def prepare_ground(beliefs: ox.Store, into: ox.Store, scope: str,
                     now: datetime) -> ox.Store:
    """Fill an empty store with what a search over one SCOPE needs, and hand it back.

    `beliefs` is read and `into` is written; both are the engine, a `pyoxigraph.Store`, and the
    caller makes the empty one. Everything that happens to a possible world afterwards happens
    to `into` the ordinary way, so this is the seam and not a wrapper.

    THREE THINGS CROSS, and then a fourth is BUILT:

    1. **Every public graph, asked rather than listed.** The record budgeted for four — world,
       derived, entailed, beliefs, 486 quads — on the reasoning that those are what the shipped
       rules read. Measured, that set makes the actuation and market CONSTRUCTs bind nothing:
       both walk `?term market:ofGood ?good`, and a valuation term is stated in a package's
       `ontology.ttl`, so it lands in the ontology graph along with the T-Box. Copying every
       public graph costs 10.4 ms and 2,646 quads on `world/loner` where the lean set is 0.6 ms
       and 165 — and the lean set is wrong in the way this function exists to prevent, since a
       pattern reaching a graph nobody copied returns an EMPTY RESULT rather than an error.
       **That measurement is also why nothing here is narrowed per scope**: fewer graphs is the
       same move under another name, and it fails the same silent way. The scope names this
       imaginarium; it does not yet cut it, and would need a slice a rule could be REFUSED
       against before it safely could.
    2. **The catalogue**, since every read inside asks it what the graphs are.
    3. **What the agent alone holds and a rule still names**: its readings, which are where the
       search starts; its predictions, which make the grounds; and its desires and wants,
       whose shapes the packages' shapes target. Whatever
       its period — a pass asks its rules at instants of its own, and a forecast holding then is
       a graph the present has not reached.
    4. **The GROUND WORLDS**, built here rather than copied: one graph per period the agent can
       see, classified `planning:GroundGraph` with the stretch it holds over, so which ground
       holds at an instant is the door's question. See `lay_ground` below for why a prediction
       has to be a diff for that to be possible at all.

    QUADS AND NOT TEXT, which is why this is not a `dump`-and-`load`: a serialise-and-reparse
    relabels blank nodes, so an observation node would come out the far side unequal to the one
    a retraction names.
    """
    #  ONE QUESTION, NOT FIVE. `graphs_of` takes as many kinds as a reader means and answers
    #  with the graphs of ANY of them, so asking kind by kind was four extra round trips to the
    #  catalogue for a set that is unioned anyway. Measured at 107 µs a call on the plans case,
    #  which is why the list is spelled out here rather than built in pieces.
    for iri in dict.fromkeys([*graphs_of(beliefs, PUBLIC, STATE, PREDICTION,
                                         DESIRE, WANT, RECORD, BELIEF),
                              catalogue_of(beliefs)]):
        if iri is None:
            continue                          # a store nobody has told anything to has no catalogue
        into.extend(beliefs.quads_for_pattern(None, None, None, ox.NamedNode(iri)))
    _lay_ground(into, scope, now)
    return into


def _foreseen(store: ox.Store) -> list[tuple[datetime, str, str | None]]:
    """Every prediction this store holds — its graph, the instant it applies, and the pattern
    it supersedes — earliest first.

    ALL THREE ARE SAID OF THE GRAPH AND NONE INSIDE IT: a prediction's contents are what it
    ADDS, which is what a prediction naturally is — `GRAPH :next_temp { :air :hasTemp 30 }` —
    and a triple saying how to retract would be one of the facts it asserts. The catalogue
    already says what a graph is, whose it is and when it holds; how it supersedes is the same
    kind of statement about it.

    THE RETRACT IS A PATTERN AND THE ADDS ARE NOT, which is the whole shape of this. What a
    forecast says is concrete — a value at an instant; what it TAKES AWAY is whatever is
    standing in that place, which nobody can name in advance. So one is data and the other is a
    CONSTRUCT over `$state`, and a keyed reading falls out of it for free: the pattern matches
    the old observation node by its key and takes it whole.

    NO HOLDER. One agent, one volume (rule 4), so the store IS the scope and a prediction in it
    is this agent's by construction.

    A PREDICTION THAT RETRACTS NOTHING is legal and means it: a forecast of something the world
    does not yet say at all — a round opening, a claim arriving — adds without superseding.
    """
    said = """
SELECT ?prediction ?at ?retracts WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?prediction a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?at .
               OPTIONAL { ?prediction orexis:retracts ?retracts } } }
ORDER BY ?at ?prediction"""
    return sorted((datetime.fromisoformat(r["at"]), r["prediction"], r.get("retracts"))
                  for r in rows(store, said, ()))


def _lay_ground(store: ox.Store, scope: str, now: datetime) -> list[str]:
    """Build one ground world per period the agent can see, classified with its stretch.

    The present is the first, and is the agent's readings as they stand. Each prediction that
    applies later is run against the ground standing before it and the diff applied; a ground
    that hashes the same as the one before it is not a period, and is dropped.

    Answers with the graphs it made, earliest first. What a READER takes is
    `graphs_of(store, GROUND_GRAPH, at=T)`.
    """

    ahead = _foreseen(store)
    here = _present(store, scope, now)
    made, marks = [here], hash_named_graph(store, here)
    opened = [now]
    for at, group in _by_instant(ahead):
        if at <= now:
            continue                    # a forecast already reached is the present's, not ahead
        #  EVERYTHING BEGINNING AT ONE INSTANT IS ONE WORLD CHANGE. A boundary is an instant,
        #  not a forecast: two drifts that both start at one o'clock describe ONE world, and
        #  forking once per forecast made two grounds with the same name and a period from the
        #  instant to itself — which holds at no instant at all, so a reader standing after it
        #  was handed NO ground and the agent went blind past the boundary. Each retract is
        #  read against the ground standing BEFORE the instant, so they supersede in parallel
        #  rather than one seeing another's work.
        added, retracts = [], []
        for prediction, supersedes in group:
            added += list(_triples(store, prediction))
            if supersedes:
                retracts.append(supersedes)
        if not added and not retracts:
            #  A forecast that changes nothing is not a period — an early-out, not a guard:
            #  the hash below reaches the same answer, having laid the graph first.
            continue
        there = _fork(store, here, _name(scope, at), added, retracts)
        mark = hash_named_graph(store, there)
        if mark == marks:
            #  THE SAME GROUND UNDER ANOTHER NAME. Nothing a met-test can read moved, so this
            #  instant answers what the one before it answered and is not a period of its own.
            forget_graph(store, there)
            continue
        #  THE ONE BEFORE IT ENDS HERE. A ground holds until the next one begins, which is not
        #  known until it does — so each is classified when its successor arrives, and the last
        #  is left open because nothing the agent can see ends it.
        classify(store, here, GROUND_GRAPH, OREXIS + "Derived", start=opened[-1], end=at)
        made.append(there)
        opened.append(at)
        here, marks = there, mark
    classify(store, here, GROUND_GRAPH, OREXIS + "Derived", start=opened[-1])
    log.debug("%s: %d ground world(s) over %d prediction(s)", scope, len(made), len(ahead))
    return made


def _present(store: ox.Store, scope: str, now: datetime) -> str:
    """The agent's readings as they stand, as a ground of its own.

    COPIED RATHER THAN USED IN PLACE. The state graph is what the agent BELIEVES; a ground is
    what a pass stands on, and a pass must be able to fork one without the belief base moving.
    """
    name = _name(scope, now)
    for source in graphs_of(store, STATE):
        update(store, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                       f"WHERE {{ GRAPH <{source}> {{ ?s ?p ?o }} }}")
    return name


def _by_instant(predictions) -> list[tuple[datetime, list[tuple[str, str | None]]]]:
    """The predictions grouped by the instant they apply, earliest first — one entry per
    BOUNDARY rather than one per forecast."""
    out: dict = {}
    for at, prediction, supersedes in predictions:
        out.setdefault(at, []).append((prediction, supersedes))
    return sorted(out.items())


def _fork(store: ox.Store, parent: str, name: str, added, retracts: list[str]) -> str:
    """The ground one boundary past `parent`: its facts, less what each prediction there
    retracts, plus what they all add.

    EVERY DELETE BEFORE ANY ADD, which is `apply_diff`'s whole job and said there: a boundary
    is ONE world change, and the predictions beginning at an instant supersede in parallel.
    """
    node = ox.NamedNode(name)
    #  THE SAME COPY A SEARCH MAKES, and the store's because it says nothing about why: a
    #  boundary forks the ground before it exactly as a step forks the world it is taken in.
    copy_graph(store, parent, name)
    #  AND THE SAME DIFF, for the same reason: every delete before any add. A prediction's
    #  retraction is bound HERE, to the ground this boundary makes, because what `$state`
    #  means is the caller's — an action's is bound to the world its step makes.
    apply_diff(store, name, added,
               [bind(text, state=Raw(f"<{name}>")) for text in retracts])
    #  AND WHICH GROUND IT CAME FROM, in the store rather than in its name. What MADE it is
    #  not said: a ground is made by predictions nobody takes, and its own period says when —
    #  which is the one thing a possible world has no answer for and a ground does.
    add_quads(store, [ox.Quad(node, ox.NamedNode(_PROV + "wasDerivedFrom"),
                              ox.NamedNode(parent), ox.NamedNode(catalogue_of(store)))])
    return name


def _triples(store: ox.Store, world: str):
    return (ox.Triple(q.subject, q.predicate, q.object) for q in quads(store, world))


def _name(scope: str, at: datetime) -> str:
    """A ground's name, for eyes: the scope it was laid for and the instant it opens at.
    Nothing depends on it — every reader asks the class."""
    stamp = at.isoformat().replace(":", "").replace("+", "p")
    return f"http://example.org/orexis/graph/ground/{scope.rsplit('/', 1)[-1]}/{stamp}"

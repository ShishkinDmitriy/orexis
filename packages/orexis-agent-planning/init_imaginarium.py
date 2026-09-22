"""Filling an imaginarium: what a search over one scope is given, and the ground it stands on.

A FUNCTION OVER TWO STORES, which is the one thing in this package that cannot be a function
over a single one. `beliefs` is read and the empty store is written; both are the engine, a
`pyoxigraph.Store`, and the caller makes the empty one. Everything that happens to a possible
world afterwards happens to that store the ordinary way, so this is the seam and not a wrapper.

ITS OWN FILE because it is its own act. `imaginarium.py` holds the doors a rule is asked
through once a world exists; this decides what a world is made OF, which is a question about
the belief base rather than about the imaginarium — and the two shared a file only because the
fill used to be three lines inside a constructor.

--- AND THE GROUND WORLDS, which are the second half of filling one --------------------------

**A PREDICTION IS AN ACTION NOBODY TAKES.** It carries the same two texts an action does —
`sh:construct` for what it makes true and `orexis:retracts` for what it takes away — and its
graph's period says WHEN it applies rather than a precondition saying whether it may. So the
timeline is laid by exactly the machinery the search walks: `effects.apply` runs the rule and
the diff is applied to the period before.

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
over, `planning:GroundGraph`, so a reader asks `graphs_of(engine, GROUND_GRAPH, at=T)` and is
handed the one world standing then. A list handed back would be a second place the answer lived
(a-reader-states-the-kinds-it-reads).
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from orexis_agent_execution.ontology import (BELIEF, DESIRE, OREXIS, PREDICTION, PUBLIC, RECORD,
                                             STATE, WANT)
from orexis_agent_execution.store import (Raw, add_quads, bind, catalogue_of, classify,
                                          construct, graphs_of, quads, query, remove_quads,
                                          rows, update)

from . import signature
from .ontology import GROUND_GRAPH


def init_imaginarium(beliefs: ox.Store, into: ox.Store, scope: str,
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
       search starts; its picks, which a conversion comes out of; its predictions, which make
       the grounds; and its desires and wants, whose shapes the packages' shapes target. Whatever
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
    private = [*graphs_of(beliefs, STATE), *graphs_of(beliefs, PREDICTION),
               *graphs_of(beliefs, DESIRE, WANT, RECORD), *graphs_of(beliefs, BELIEF)]
    for iri in dict.fromkeys([*graphs_of(beliefs, PUBLIC), catalogue_of(beliefs), *private]):
        if iri is None:
            continue                          # a store nobody has told anything to has no catalogue
        into.extend(beliefs.quads_for_pattern(None, None, None, ox.NamedNode(iri)))
    lay_ground(into, scope, now)
    return into


log = logging.getLogger("ground")

#  EVERY PREDICTION, WHEN IT APPLIES, AND WHAT IT SUPERSEDES. All three are said of the GRAPH
#  and none inside it: a prediction's contents are what it ADDS, which is what a prediction
#  naturally is — `GRAPH :next_temp { :air :hasTemp 30 }` — and a triple saying how to retract
#  would be one of the facts it asserts. The catalogue already says what a graph is, whose it
#  is and when it holds; how it supersedes is the same kind of statement about it.
#
#  THE RETRACT IS A PATTERN AND THE ADDS ARE NOT, which is the whole shape of this. What a
#  forecast says is concrete — a value at an instant; what it TAKES AWAY is whatever is
#  standing in that place, which nobody can name in advance. So one is data and the other is a
#  CONSTRUCT over `$state`, and a keyed reading falls out of it for free: the pattern matches
#  the old observation node by its key and takes it whole.
_WHEN_Q = """
SELECT ?prediction ?at ?retracts WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?prediction a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?at .
               OPTIONAL { ?prediction orexis:retracts ?retracts } } }
ORDER BY ?at ?prediction"""


def foreseen(engine: ox.Store) -> list[tuple[datetime, str, str | None]]:
    """Every prediction this store holds — its graph, the instant it applies, and the pattern
    it supersedes — earliest first.

    NO HOLDER. One agent, one volume (rule 4), so the store IS the scope and a prediction in it
    is this agent's by construction.

    A PREDICTION THAT RETRACTS NOTHING is legal and means it: a forecast of something the world
    does not yet say at all — a round opening, a claim arriving — adds without superseding.
    """
    return sorted((datetime.fromisoformat(r["at"]), r["prediction"], r.get("retracts"))
                  for r in rows(engine, _WHEN_Q, ()))


def lay_ground(engine: ox.Store, scope: str, now: datetime) -> list[str]:
    """Build one ground world per period the agent can see, classified with its stretch.

    The present is the first, and is the agent's readings as they stand. Each prediction that
    applies later is run against the ground standing before it and the diff applied; a ground
    that hashes the same as the one before it is not a period, and is dropped.

    Answers with the graphs it made, earliest first — for a caller that wants to say how many
    there were. What a READER takes is `graphs_of(engine, GROUND_GRAPH, at=T)`.
    """
    keys = signature.keys_of(lambda text: query(engine, text, graphs_of(engine, PUBLIC)))
    public = graphs_of(engine, PUBLIC)

    here = _present(engine, scope, now)
    made, marks = [here], signature.facts(_triples(engine, here), keys)
    opened = [now]
    for at, prediction, supersedes in foreseen(engine):
        if at <= now:
            continue                    # a forecast already reached is the present's, not ahead
        added = list(_triples(engine, prediction))
        retracted = _superseded(engine, supersedes, [*public, here], here)
        if not added and not retracted:
            continue                    # a prediction that changes nothing is not a period
        there = _fork(engine, here, _name(scope, at), added, retracted)
        mark = signature.facts(_triples(engine, there), keys)
        if mark == marks:
            #  THE SAME GROUND UNDER ANOTHER NAME. Nothing a met-test can read moved, so this
            #  instant answers what the one before it answered and is not a period of its own.
            update(engine, f"DROP SILENT GRAPH <{there}>")
            continue
        #  THE ONE BEFORE IT ENDS HERE. A ground holds until the next one begins, which is not
        #  known until it does — so each is classified when its successor arrives, and the last
        #  is left open because nothing the agent can see ends it.
        classify(engine, here, GROUND_GRAPH, OREXIS + "Derived", start=opened[-1], end=at)
        made.append(there)
        opened.append(at)
        here, marks = there, mark
    classify(engine, here, GROUND_GRAPH, OREXIS + "Derived", start=opened[-1])
    log.debug("%s: %d ground world(s) over %d prediction(s)", scope, len(made),
              len(foreseen(engine)))
    return made


def _present(engine: ox.Store, scope: str, now: datetime) -> str:
    """The agent's readings as they stand, as a ground of its own.

    COPIED RATHER THAN USED IN PLACE. The state graph is what the agent BELIEVES; a ground is
    what a pass stands on, and a pass must be able to fork one without the belief base moving.
    """
    name = _name(scope, now)
    for source in graphs_of(engine, STATE):
        update(engine, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                       f"WHERE {{ GRAPH <{source}> {{ ?s ?p ?o }} }}")
    return name


def _superseded(engine: ox.Store, pattern: str | None, graphs, state: str) -> list:
    """What this prediction takes away: its `orexis:retracts` CONSTRUCT run against the ground
    standing before it, with `$state` bound to that ground. Empty where it states none.

    A PATTERN THAT WILL NOT RUN RETRACTS NOTHING, loudly. A prediction whose text the engine
    refuses would otherwise add its value beside the one it meant to replace, and a shape
    holding over every value would still see the old one — which is the exact failure the
    retract exists to close, arriving by another door.
    """
    if not pattern:
        return []
    try:
        return list(construct(engine, bind(pattern, state=Raw(f"<{state}>")), graphs))
    except Exception as exc:                                        # noqa: BLE001
        log.error("a prediction's retract would not run, so it supersedes nothing: %s", exc)
        return []


def _fork(engine: ox.Store, parent: str, name: str, added, retracted) -> str:
    """The ground one prediction past `parent`: its facts, less what the prediction retracts,
    plus what it adds. Retraction before addition, for the reason `Imaginarium.reached` gives —
    a construct may reuse the very node its retraction names."""
    node = ox.NamedNode(name)
    update(engine, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                   f"WHERE {{ GRAPH <{parent}> {{ ?s ?p ?o }} }}")
    remove_quads(engine, [ox.Quad(t.subject, t.predicate, t.object, node) for t in retracted])
    add_quads(engine, (ox.Quad(t.subject, t.predicate, t.object, node) for t in added))
    return name


def _triples(engine: ox.Store, world: str):
    return (ox.Triple(q.subject, q.predicate, q.object) for q in quads(engine, world))


def _name(scope: str, at: datetime) -> str:
    """A ground's name, for eyes: the scope it was laid for and the instant it opens at.
    Nothing depends on it — every reader asks the class."""
    stamp = at.isoformat().replace(":", "").replace("+", "p")
    return f"http://example.org/orexis/graph/ground/{scope.rsplit('/', 1)[-1]}/{stamp}"

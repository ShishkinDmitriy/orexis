"""The GROUND WORLDS a pass stands on: the present, and what each prediction makes of it.

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

from orexis_agent_execution.ontology import OREXIS, PREDICTION, PUBLIC, STATE
from orexis_agent_execution.store import (Raw, add_quads, classify, graphs_of, quads,
                                          quads_for_pattern, remove_quads, rows, update)

from . import effects, signature
from .ontology import GROUND_GRAPH

log = logging.getLogger("ground")

#  EVERY PREDICTION AND WHEN IT APPLIES: the graphs of predictions, with the instant each
#  begins to hold. The period is on the GRAPH, as every stretch here is; the rule is on the
#  node inside it, as every effect here is.
_WHEN_Q = """
SELECT ?prediction ?at WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?at }
  GRAPH ?g { ?prediction a orexis:Action } }
ORDER BY ?at ?prediction"""


def foreseen(engine: ox.Store) -> list[tuple[datetime, str]]:
    """Every prediction this store holds, with the instant it applies, earliest first.

    NO HOLDER. One agent, one volume (rule 4), so the store IS the scope and a prediction in it
    is this agent's by construction.
    """
    return sorted((datetime.fromisoformat(r["at"]), r["prediction"])
                  for r in rows(engine, _WHEN_Q, ()))


def lay_ground(engine: ox.Store, scope: str, now: datetime) -> list[str]:
    """Build one ground world per period the agent can see, classified with its stretch.

    The present is the first, and is the agent's readings as they stand. Each prediction that
    applies later is run against the ground standing before it and the diff applied; a ground
    that hashes the same as the one before it is not a period, and is dropped.

    Answers with the graphs it made, earliest first — for a caller that wants to say how many
    there were. What a READER takes is `graphs_of(engine, GROUND_GRAPH, at=T)`.
    """
    keys = signature.keys_of(lambda text: _ask(engine, text, graphs_of(engine, PUBLIC)))
    public = graphs_of(engine, PUBLIC)
    declared = graphs_of(engine, PREDICTION)

    here = _present(engine, scope, now)
    made, marks = [here], signature.facts(_triples(engine, here), keys)
    opened = [now]
    for at, prediction in foreseen(engine):
        if at <= now:
            continue                    # a forecast already reached is the present's, not ahead
        added, retracted = effects.apply(engine, prediction, [*public, here],
                                         declared=declared, state=Raw(f"<{here}>"))
        if not added and not retracted:
            continue                    # a prediction that changes nothing is not a period
        there = _fork(engine, here, _name(scope, at), added, retracted, keys)
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


def _fork(engine: ox.Store, parent: str, name: str, added, retracted, keys: dict) -> str:
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


def _ask(engine: ox.Store, text: str, graphs):
    from orexis_agent_execution.store import query
    return query(engine, text, graphs)

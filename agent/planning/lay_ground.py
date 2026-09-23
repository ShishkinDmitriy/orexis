"""Laying the ground worlds: what the agent's own knowledge comes to over each period, one
graph per period, in the store a pass stands in.

**A PREDICTION IS AN ACTION NOBODY TAKES.** What it makes true is its graph's own contents —
concrete, because a forecast is a value at an instant — and what it takes away is
`orexis:retracts` on its catalogue row, a `DELETE … WHERE` naming `GRAPH $state`, because what
is standing in that place is not something a forecast can name in advance. Its period says
WHEN it applies rather than a precondition saying whether it may. So the timeline is laid by
exactly the machinery the search walks: the readings holding at the instant, each
prediction's retraction run against them, each prediction's facts added.

**A GROUND IS THE WORLD AT ONE INSTANT, AND EVERY BOUNDARY IS ONE** (#783). A boundary is an
instant at which something the agent holds begins or ENDS: a prediction's window opening, a
reading's standing as the present running out, a forecast's window closing. At each one the
ground is built from what holds THEN — the graphs of readings holding at the instant, and
every prediction whose window covers it, applied in the order their windows open — and never
by forking the ground before it, because a fork carries forward what should have ended. A
reading whose horizon has passed is not in the ground past it; a prediction whose window has
BEGUN is in the present's, standing in for the reading it superseded — which is what makes
a forecast the drift wrote at noon the world at a quarter past when the sensor is late, and
unmeasured the silence past the last window rather than the first missed reading. Two things
were refused on the way: forking each ground from the last, which is what stood here and
knew no ends, and skipping a prediction already begun as "the present's", which handed the
present nothing where the reading had lapsed.

WHY IT HAD TO BECOME A DIFF. A prediction used to be a STATE — a graph holding the reading it
foretold — and a door handed a reader every graph holding at an instant, so a met-test asked at
a foreseen instant saw the reading AND the prediction of it. A shape holds over EVERY value, so
the stale one still violated: measured, a tank low now and a forecast refilling it read *unmet
from twelve, lifts NEVER*, because the present's 5 outlived the forecast's 20. Nothing was
wrong with the forecast; there was no place in the pass where it REPLACED anything.

**AND THE PERIODS COLLAPSE.** Each ground is hashed as a possible world is, and where two
neighbouring boundaries reach the same facts the second is not a period at all: nothing a
met-test can read moved, so nothing it could answer differs there. Measured on three
boundaries whose middle prediction restated the present — three boundaries, two grounds. That
is what bounds the judging: a desire is asked once per DISTINCT ground rather than once per
boundary, so a store thick with forecasts that say nothing new costs a pass nothing.

**WHAT IS BUILT IS CLASSIFIED, NOT RETURNED.** Each ground is a graph with the stretch it holds
over, `planning:GroundGraph`, so a reader asks `graphs_of(store, GROUND_GRAPH, at=T)` and is
handed the one world standing then. A list handed back would be a second place the answer lived
(a-reader-states-the-kinds-it-reads).
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import OREXIS
from agent.hash_named_graph import hash_named_graph
from agent.store import Raw, add_quads, bind, catalogue_of, classify, forget_graph, quads, rows, update

from .ontology import GROUND_GRAPH

_PROV = "http://www.w3.org/ns/prov#"

log = logging.getLogger("lay_ground")

#  EVERYTHING A GROUND IS MADE OF: every graph of readings and every prediction, with the
#  stretch it holds over and, for a prediction, the pattern it supersedes.
#
#  ALL THREE ARE SAID OF THE GRAPH AND NONE INSIDE IT: a prediction's contents are what it
#  ADDS, which is what a prediction naturally is — `GRAPH :next_temp { :air :hasTemp 30 }` —
#  and a triple saying how to retract would be one of the facts it asserts. The catalogue
#  already says what a graph is, whose it is and when it holds; how it supersedes is the same
#  kind of statement about it.
#
#  THE RETRACT IS A PATTERN AND THE ADDS ARE NOT, which is the whole shape of this. What a
#  forecast says is concrete — a value at an instant; what it TAKES AWAY is whatever is
#  standing in that place, which nobody can name in advance. So one is data and the other is a
#  CONSTRUCT over `$state`, and a keyed reading falls out of it for free: the pattern matches
#  the old observation node by its key and takes it whole.
#
#  NO HOLDER. One agent, one volume (rule 4), so the store IS the scope and a prediction in it
#  is this agent's by construction.
#
#  A PREDICTION THAT RETRACTS NOTHING is legal and means it: a forecast of something the world
#  does not yet say at all — a round opening, a claim arriving — adds without superseding.
_HELD_Q = """
SELECT DISTINCT ?g ?kind ?start ?end ?retracts WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a ?kind . VALUES ?kind { orexis:StateGraph orexis:PredictionGraph }
               FILTER(isIRI(?g))
               OPTIONAL { ?g dcterms:temporal ?p .
                          OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } }
               OPTIONAL { ?g orexis:retracts ?retracts } } }
ORDER BY ?start ?g"""

_STATE = OREXIS + "StateGraph"
_PREDICTION = OREXIS + "PredictionGraph"


def lay_ground(store: ox.Store, now: datetime) -> list[str]:
    """Build one ground world per period the agent can see, classified with its stretch.

    The present is the first, and holds what the readings say at `now` with every prediction
    whose window has begun applied. Each later boundary — an instant at which a reading or a
    prediction begins or ends — is built the same way from what holds then; a ground that
    hashes the same as the one before it is not a period, and is dropped.

    Answers with the graphs it made, earliest first. What a READER takes is `world_at`.

    PUBLIC, AND IN PLACE: it lays the grounds into whichever store it is handed. `prepare_ground`
    lays them into the imaginarium it fills; a case that holds the derivation to the store it
    leaves lays them into the case's own store, so every graph the case declared — a ledger
    among them — stays where the derivation reads it.
    """
    held = _held(store)
    boundaries = sorted({now} | {t for g in held for t in (g["start"], g["end"]) if t is not None and t > now})
    made: list[str] = []
    marks: str | None = None
    opened: datetime | None = None
    for at in boundaries:
        readings = [g["g"] for g in held if g["kind"] == _STATE and _holding(g, at)]
        foreseen = [g for g in held if g["kind"] == _PREDICTION and _holding(g, at)]
        there = _lay(store, _name(at), readings, foreseen, made[-1] if made else None)
        mark = hash_named_graph(store, there)
        if made and mark == marks:
            #  THE SAME GROUND UNDER ANOTHER NAME. Nothing a met-test can read moved, so this
            #  instant answers what the one before it answered and is not a period of its own.
            forget_graph(store, there)
            continue
        if made:
            #  THE ONE BEFORE IT ENDS HERE. A ground holds until the next one begins, which is
            #  not known until it does — so each is classified when its successor arrives, and
            #  the last is left open because nothing the agent can see ends it.
            classify(store, made[-1], GROUND_GRAPH, OREXIS + "Derived", start=opened, end=at)
        made.append(there)
        opened, marks = at, mark
    classify(store, made[-1], GROUND_GRAPH, OREXIS + "Derived", start=opened)
    log.debug("%d ground world(s) over %d boundaries", len(made), len(boundaries))
    return made


def _held(store: ox.Store) -> list[dict]:
    out = []
    for r in rows(store, _HELD_Q, ()):
        out.append({"g": r["g"], "kind": r["kind"], "retracts": r.get("retracts"),
                    "start": datetime.fromisoformat(r["start"]) if r.get("start") else None,
                    "end": datetime.fromisoformat(r["end"]) if r.get("end") else None})
    return out


def _holding(graph: dict, at: datetime) -> bool:
    """Whether a graph holds at `at`: from its start, inclusive, to its end, exclusive, and
    always where it states neither — the same rule the store's door applies."""
    return (graph["start"] is None or graph["start"] <= at) and (graph["end"] is None or at < graph["end"])


def _lay(store: ox.Store, name: str, readings: list[str], foreseen: list[dict], before: str | None) -> str:
    """The ground standing at one instant: the readings holding then, less what each
    prediction holding then retracts, plus what they all add — the order the search's own
    fork keeps, every retraction read against the readings before any addition, so the
    predictions beginning together supersede in parallel rather than one seeing another's
    work.

    COPIED RATHER THAN USED IN PLACE. The graphs of readings are what the agent BELIEVES; a
    ground is what a pass stands on, and a pass must be able to fork one without the belief
    base moving. A prediction's retraction is bound HERE, to the ground this boundary makes,
    because what `$state` means is the caller's — an action's is bound to the world its step
    makes.
    """
    _relaid(store, name)
    for source in readings:
        update(store, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} WHERE {{ GRAPH <{source}> {{ ?s ?p ?o }} }}")
    #  EVERYTHING BEGINNING AT ONE INSTANT IS ONE WORLD CHANGE, and a window that began later
    #  supersedes one that began earlier: the predictions holding at the instant are applied
    #  group by group in the order their windows open — every retraction of a group read
    #  against what stands, then every addition of it — so two forecasts opening together
    #  supersede in parallel, and a refill foreseen at one o'clock replaces the dip foreseen at
    #  half past that has not ended, exactly as a fork after a fork would.
    by_start: dict = {}
    for prediction in foreseen:
        by_start.setdefault(prediction["start"], []).append(prediction)
    for _, group in sorted(by_start.items(), key=lambda kv: (kv[0] is not None, kv[0])):
        for prediction in group:
            if prediction["retracts"]:
                try:
                    update(store, bind(prediction["retracts"], state=Raw(f"<{name}>")))
                except Exception as exc:                                # noqa: BLE001
                    #  A RETRACTION THAT WILL NOT RUN RETRACTS NOTHING, LOUDLY: a package's
                    #  bug must not take an agent down, and the old value standing beside
                    #  the new is what the log then says.
                    log.error("a prediction's retraction would not run, so it retracts nothing: %s", exc)
        for prediction in group:
            add_quads(store, (ox.Quad(q.subject, q.predicate, q.object, ox.NamedNode(name))
                              for q in quads(store, prediction["g"])))
    if before is not None:
        #  AND WHICH GROUND CAME BEFORE IT, in the store rather than in its name. What MADE it
        #  is not said: a ground is made by predictions nobody takes and readings that end,
        #  and its own period says when — which is the one thing a possible world has no
        #  answer for and a ground does.
        add_quads(store, [ox.Quad(ox.NamedNode(name), ox.NamedNode(_PROV + "wasDerivedFrom"),
                                  ox.NamedNode(before), ox.NamedNode(catalogue_of(store)))])
    return name


#  THE VERDICTS ABOUT A GROUND, with the violation rows hanging off each.
_UNWEIGH_U = """
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x a planning:Weighing ; planning:weighs $world ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"""


def _relaid(store: ox.Store, name: str) -> None:
    """Take back a ground standing under the name this pass is about to lay under — its
    facts, its row and every weighing of it.

    THE IMAGINARIUM OUTLIVES THE PASS, and a ground is named for its instant, so a boundary the
    last pass's predictions reached too — a forecast at one o'clock, seen from noon and again
    from a minute past — is laid under the name it had. Laid on top, the old facts would stand
    beside the new; kept, its weighings would be verdicts about what it used to hold, and
    `unweighed` would not ask again. The ground of the last PRESENT keeps its name and its
    rows: `reroot` is what decides whether the present is the world it was.
    """
    forget_graph(store, name)
    update(store, bind(_UNWEIGH_U, world=name))


def _name(at: datetime) -> str:
    """A ground's name, for eyes: the instant it opens at. Nothing depends on it — every
    reader asks the class. It carried the scope's name too, and the scope was a parameter
    for that alone: one imaginarium holds one scope's grounds, so the name said nothing."""
    stamp = at.isoformat().replace(":", "").replace("+", "p")
    return f"http://example.org/orexis/graph/ground/{stamp}"

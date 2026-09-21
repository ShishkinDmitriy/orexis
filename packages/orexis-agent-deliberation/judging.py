"""JUDGING A DESIRE: running its met-test over the world as it stands and as it is predicted
to stand, and saying what it read — as WITNESSES, computed and never stored.

A desire is universal and a want is existential: the met-test's violation rows are the
instances in trouble, each one a witness, and `derive_wants` mints a want per cluster of them.
There is no third thing between the two. A `deliberation:Judgment` row used to stand there —
the met-test's answer per desire per instant, written to a working graph and read back — and
it is gone: everything it carried a WANT carries now, and what it was for, telling the next
step what the met-test read, is what a witness is.

THIS IS THE ONLY PLACE THAT READS A PREDICTION. What a desire reads at a foreseen instant is
a question about the world, asked here and nowhere else: `derive_wants` asks it to mint and
`crossing_of` asks it for an instant, and both get the same answer from the same code rather
than from two paths that could disagree.

WHAT A CALLER TAKES IS THE ANSWER TO ITS OWN QUESTION. A `Witness` is the grain a want is
minted at and `derive_wants` clusters on it, so it lives here beside `read_ahead`, which
dedups on two of its fields. Every other caller wants an INSTANT — the crossing, or whether
a want is still unmet by one — and is handed that, rather than rows to reduce itself.

A FUNCTION OVER THE STORE: handed the engine, a `pyoxigraph.Store`, and nothing else. Which
graphs hold desires, which are predictions and which hold at an instant, the catalogue says;
who holds a desire, the desire's own graph says; what a met-test means, its shape says. The
present is the clock's, the one read outside the store.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox
import rdflib

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import FORESEEN, OREXIS
from orexis_agent_progression.store import NAMESPACES, answer, bind, bindings, graphs_holding, instant

log = logging.getLogger("judging")

#  EVERY DESIRE THE STORE HOLDS, who holds it and its met-test, from the graphs of desires
#  holding at the present — the roots graph states no period, the world's asserted graph
#  none, and a graph of desires with one is read while it holds. A desire, its holder and its
#  met-test are written together — one rule derives them, one file ratifies them — so the
#  pattern matches within one graph.
_DESIRES_Q = """
SELECT DISTINCT ?holder ?desire ?shape WHERE {
  GRAPH ?g { ?holder orexis:holds ?desire . ?desire a orexis:Desire .
             OPTIONAL { ?desire orexis:metWhen ?shape } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph .
               OPTIONAL { ?g dcterms:temporal ?period .
                          OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } }
               FILTER(!BOUND(?start) || $now >= ?start) FILTER(!BOUND(?end) || $now < ?end) } }
ORDER BY ?holder ?desire"""

#  ONE desire, its holder and its met-test — for a reader asking about one.
_ONE_Q = """
SELECT ?holder ?shape WHERE {
  GRAPH ?g { ?holder orexis:holds $desire . OPTIONAL { $desire orexis:metWhen ?shape } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph } }
ORDER BY ?holder"""

#  WHEN THE HOLDER FORESEES: the start of every prediction of theirs, whatever its window —
#  the future states a desire is judged at, given to this and never computed here (#643).
_STARTS_Q = """
SELECT DISTINCT ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?start .
               OPTIONAL { ?g orexis:beliefsOf ?owner } FILTER(!BOUND(?owner) || ?owner = $holder) } }
ORDER BY ?start"""

#  WHERE THE SHAPES LIVE: every graph of desires and of wants, whatever its period — a
#  desire's shape and its blank-node closure sit in a desire graph whole, a derived want's own
#  in its want graph, and the whole belief base parsed into rdflib cost half a second per
#  shape for a closure of forty triples (#711).
_SHAPE_GRAPHS_Q = """
SELECT DISTINCT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind . FILTER(isIRI(?g))
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } }
ORDER BY ?g"""

#  ONE HELD NODE, its holder and whichever met-test it carries — over the graphs of desires
#  AND of wants, because the three kinds that reach this are in different families: a desire
#  the packages authored, a want the derivation minted, and a want a world RATIFIED directly,
#  which has no desire above it and so is never minted at all.
_HELD_Q = """
SELECT ?holder ?met ?unmet WHERE {
  GRAPH ?g { ?holder orexis:holds $node .
             OPTIONAL { $node orexis:metWhen ?met }
             OPTIONAL { $node orexis:unmetWhen ?unmet } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } } LIMIT 1"""

#  WHAT A WANT NARROWS ITS DESIRE TO: its own met-test, which is the desire's carved to the
#  cluster the want was minted from and targeted at its instance.
_WANTS_SHAPE_Q = """
SELECT ?holder ?shape WHERE {
  GRAPH ?g { ?holder orexis:holds $want . $want orexis:metWhen ?shape }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:WantGraph } } LIMIT 1"""


@dataclass(frozen=True)
class Witness:
    """One way a desire is failing, and when it first does: the instance that failed, the
    constraint it failed, what that constraint is about where its block says, WHICH WAY it
    broke where the block says that, and the instant.

    A universal is refuted by a witness, and the want minted under it is the universal
    instantiated at that witness (one-function-mints-every-want). It is what a
    `deliberation:Judgment`'s result was, and it is computed rather than stored: a want is
    where any of this is kept.
    """

    instance: str
    constraint: str
    about: str | None
    at: datetime
    side: str | None = None


def desires_in(store: ox.Store, now: datetime) -> list[tuple[str, str, str | None]]:
    """Every desire the store holds at `now`, as `(holder, desire, met-test or None)`. One
    agent, one volume, so the holder is the agent; a store holding several agents' desires
    answers for each."""
    return [(r["holder"].value, r["desire"].value,
             r["shape"].value if r["shape"] is not None else None)
            for r in store.query(bind(_DESIRES_Q, now=instant(now)), prefixes=NAMESPACES)]


def read_now(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str,
             shape: str | None, now: datetime) -> list[Witness] | None:
    """What this desire's met-test reads at the PRESENT: its witnesses, empty where it is met,
    None where there is no compilable met-test to ask."""
    select = compiled(shapes, shape, desire)
    if select is None:
        return None
    return _witnesses_at(store, select, holder, now, now)


def read_ahead(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str,
               shape: str | None, now: datetime) -> list[Witness]:
    """Every (instance, constraint) this desire's met-test reads unmet at a FORESEEN instant,
    each at the EARLIEST instant it does — the instants being every prediction's start, where
    the dataset holds the prediction beside the present (#643).

    A CROSSING is the earliest of these: the instant the world a desire is about is judged to
    leave what the desire wants. The present is excluded — a desire unmet now is pursued as
    itself, and a crossing is a thing in the future.
    """
    select = compiled(shapes, shape, desire)
    if select is None:
        return []
    seen: dict[tuple[str, str], Witness] = {}
    for at in _starts(store, holder):
        for w in _witnesses_at(store, select, holder, at, now) or []:
            seen.setdefault((w.instance, w.constraint), w)
    return sorted(seen.values(), key=lambda w: (w.at, w.instance, w.constraint))


def crossing_of(store: ox.Store, desire: str) -> datetime | None:
    """When the world this desire is about is judged to leave what the desire wants, or None:
    the earliest instant its met-test reads unmet ahead of now.

    ASKED OF A DESIRE AND NEVER OF A WANT. A want has no crossing — it is what a crossing
    produced, and it carries the instant it must hold at; whether it is still in trouble by
    then is `unmet_by`.

    THE INSTANT, AND NOT THE ROWS IT IS READ FROM. This handed back its witnesses and was
    called `witnesses_of`, and its one caller took `.at` off the first and dropped the rest —
    through `pursuit.crossing_of`, which named the question this now answers, which
    `pursuit.foreseen` then named a third time and nobody called. A `Witness` is the grain a
    want is minted at (`derive_wants` clusters on it); a crossing is an instant, and a reader
    that wants one should not have to know what the other is.
    """
    found = _one(store, desire)
    if found is None:
        return None
    holder, shape = found
    witnesses = read_ahead(store, shapes_in(store), holder, desire, shape, clock.now())
    return witnesses[0].at if witnesses else None


def unmet_by(store: ox.Store, want: str, until: datetime) -> datetime | None:
    """The earliest instant at or before `until` at which this WANT's own met-test still reads
    unmet, or None where it does not.

    THE QUESTION THE CONTAINER ASKS when it presents a want that must hold at an instant: the
    want was minted because its desire read unmet there, and a later reading may have moved
    the corridor so that it no longer does — a dose lifts the pot, and the want its crossing
    produced reads met. Asked of the WANT'S OWN shape, which is the desire's narrowed to the
    cluster it was minted from and targeted at its instance, so a want about one tank is not
    held to another's prediction.
    """
    found = _one(store, want, want=True)
    if found is None:
        return None
    holder, shape = found
    if shape is None:
        return None
    select = compiled(shapes_in(store), shape, want)
    if select is None:
        return None
    now = clock.now()
    for at in _starts(store, holder):
        if at > until:
            break
        if _witnesses_at(store, select, holder, at, now):
            return at
    return None


def unmet_now(store: ox.Store, node: str) -> bool | None:
    """Does this node's OWN met-test read unmet at the present — None where it carries none.

    THE QUESTION THE CONTAINER ASKS of every want it presents: the want was minted because
    its desire read unmet, and a later reading may have moved the corridor so that its own
    instance no longer does — a dose lifts one pot while the others stay dry. `unmet_by` is
    the same question at a FORESEEN instant; this is it now.

    COMPILED TO THE LAW, not to the report. `compiled` makes the select whose rows say WHICH
    instance broke WHICH constraint — the grain the derivation mints at — and this wants a
    boolean, so it takes the compiler that answers one: the same law the planner holds
    candidates to, held to the report by parity (tests/test_violation.py).

    ITS OWN, and the test is that the shape is not the node itself: a want minted before
    wants carried one is judged as its root is, and says so by returning None.
    """
    from orexis_agent_progression.violation import unmet_select

    rows = bindings(answer(store, bind(_HELD_Q, node=node)))
    if not rows or rows[0].get("met") is None or rows[0]["met"] == node:
        return None
    holder, met = rows[0]["holder"], rows[0]["met"]
    now = clock.now()
    try:
        select = unmet_select(shapes_in(store).cbd(rdflib.URIRef(met)), rdflib.URIRef(met))
        return bool(_witnesses_at(store, select, holder, now, now))
    except Exception as exc:                                        # noqa: BLE001
        #  A MET-TEST THAT WILL NOT RUN says nothing rather than saying unmet: this answers
        #  about a want whose ROOT has a verdict already, and the caller falls back to it.
        #  Where nothing else has one — an avoided pattern the kernel lifts — the loud
        #  direction is the other way, which is why `agent/pursuing.py` still judges those
        #  itself: they are compiled from PUBLIC knowledge, where a package's shape lives,
        #  and this reads the graphs of desires and wants, where a derived want's own does.
        log.warning("%s: its own met-test would not run: %s", node.rsplit("#", 1)[-1], exc)
        return None


def shapes_in(store: ox.Store) -> rdflib.Graph:
    """Every graph of desires and of wants, parsed once — where a desire's shape lives with its
    blank-node closure, and a derived want's own. N-Triples, since it concatenates and rdflib
    parses it in a fraction of Turtle's time; the engine's blank-node labels are its own, so
    two graphs' nodes never collide in one text."""
    out = io.BytesIO()
    for row in store.query(_SHAPE_GRAPHS_Q, prefixes=NAMESPACES):
        store.dump(output=out, format=ox.RdfFormat.N_TRIPLES, from_graph=row["g"])
    shapes = rdflib.Graph()
    if out.tell():
        shapes.parse(data=out.getvalue().decode(), format="nt")
    return shapes


def compiled(shapes: rdflib.Graph, shape: str | None, of: str) -> str | None:
    """`shape` compiled to the select whose rows are its VIOLATIONS — `?this`, which
    constraint, `?_about` and `?_side` where the constraint's block says them — or None, with
    a word in the log, where there is no shape or the compiler refuses it.

    THE REPORT AND NOT THE FOCUS NODES (one-function-mints-every-want): a desire universal over
    several properties fails per property, and the rows are what say which. The planner
    compiles the same shape the same way for the law it holds candidates to."""
    from orexis_agent_progression.violation import Unsupported, report_select

    if shape is None:
        return None
    try:
        return report_select(shapes.cbd(rdflib.URIRef(shape)), rdflib.URIRef(shape))
    except Unsupported as exc:
        log.warning("%s: its met-test cannot be compiled, so it is not judged: %s",
                    of.rsplit("#", 1)[-1], exc)
        return None


def _one(store: ox.Store, node: str, want: bool = False) -> tuple[str, str | None] | None:
    """Who holds one desire — or one want — and what its met-test is, or None where no graph
    of that kind holds it."""
    if want:
        rows_ = bindings(answer(store, bind(_WANTS_SHAPE_Q, want=node)))
        return (rows_[0]["holder"], rows_[0]["shape"]) if rows_ else None
    rows_ = list(store.query(bind(_ONE_Q, desire=node), prefixes=NAMESPACES))
    if not rows_:
        return None
    return rows_[0]["holder"].value, (rows_[0]["shape"].value
                                      if rows_[0]["shape"] is not None else None)


def _starts(store: ox.Store, holder: str) -> list[datetime]:
    return [datetime.fromisoformat(row["start"].value)
            for row in store.query(bind(_STARTS_Q, holder=holder), prefixes=NAMESPACES)]


def _witnesses_at(store: ox.Store, select: str, holder: str, at: datetime,
                  now: datetime) -> list[Witness] | None:
    """The met-test's rows over the graphs `holder`'s desire is judged over at `at`, as
    witnesses — one per distinct row, since two predictions holding at one instant give one
    instance two offending values and both are told. None where the engine refuses the text.

    ONE SELECT PER DESIRE PER INSTANT, and not one union of them: the compiler measured a
    single UNION of every shape at thirteen times the cost of the selects asked one by one.
    """
    graphs = [ox.NamedNode(g) for g in graphs_holding(store, FORESEEN, holder=holder, at=at, now=now)]
    try:
        found = store.query(select, prefixes=NAMESPACES, default_graph=graphs)
        names = [v.value for v in found.variables]
        seen: dict[tuple, Witness] = {}
        for solution in found:
            row = {name: solution[name] for name in names if solution[name] is not None}
            seen.setdefault(tuple(sorted((k, str(v)) for k, v in row.items())), Witness(
                instance=row["this"].value,
                constraint=row["_constraint"].value if "_constraint" in row else "",
                about=row["_about"].value if "_about" in row else None,
                side=row["_side"].value if "_side" in row else None,
                at=at))
    except Exception as exc:                                        # noqa: BLE001
        log.error("a met-test could not be read at %s: %s", at, exc)
        return None
    return [seen[key] for key in sorted(seen)]


VIOLATION_IS = OREXIS + "violationIs"

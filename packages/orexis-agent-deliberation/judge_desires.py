"""`judge_desires`: every desire judged at the present and at every foreseen instant, the
judgments written to the store — the first of the road's two functions
(judge-desires-then-derive-wants), and a FUNCTION OVER THE STORE: handed the engine, a
`pyoxigraph.Store`, and nothing else. What it reads it asks of the store in its own texts —
which graphs hold desires, which are predictions and which hold at an instant, the catalogue
says; who holds a desire, the desire's own graph says; what a met-test means, its shape says
— and what it concludes it writes back. The one thing not in the store is the present, which
is the clock's, the layer's one read of time.

IT IS THE ONLY THING HERE THAT READS A PREDICTION. What a desire read at a foreseen instant
is written down, so every other reader of it reads the judgments — `derive_wants` to mint the
wants, `judgments.witnesses_of` to say where a crossing is. After the call, the store says what
each desire read; nothing comes back and nothing is kept in hand. `pursuit` calls the two in
turn when a pass stands on a root or a want, and the ledger when a claim arrives.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime

import pyoxigraph as ox
import rdflib

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import FORESEEN
from orexis_agent_progression.store import NAMESPACES, bind, graphs_holding, instant

from .judgments import save_judgments

log = logging.getLogger("judge_desires")

#  EVERY DESIRE THE STORE HOLDS, who holds it and its met-test, from the graphs of desires
#  holding at the present — the roots graph states no period, the world's asserted graph
#  none, and a graph of desires with one is read while it holds. A desire, its holder and its
#  met-test are written together — one rule derives them, one file ratifies them — so the
#  pattern matches within one graph.
_ROOTS_Q = """
SELECT DISTINCT ?holder ?desire ?shape WHERE {
  GRAPH ?g { ?holder orexis:holds ?desire . ?desire a orexis:Desire .
             OPTIONAL { ?desire orexis:metWhen ?shape } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph .
               OPTIONAL { ?g dcterms:temporal ?period .
                          OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } }
               FILTER(!BOUND(?start) || $now >= ?start) FILTER(!BOUND(?end) || $now < ?end) } }
ORDER BY ?holder ?desire"""

#  WHEN THE HOLDER FORESEES: the start of every prediction of theirs, whatever its window —
#  the future states this judges at, given to it and never computed here (#643).
_STARTS_Q = """
SELECT DISTINCT ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?start .
               OPTIONAL { ?g orexis:beliefsOf ?owner } FILTER(!BOUND(?owner) || ?owner = $holder) } }
ORDER BY ?start"""

#  WHERE THE SHAPES LIVE: every graph of desires and of wants, whatever its period — a root's
#  shape and its blank-node closure sit in a desire graph whole, a derived want's own in its
#  want graph, and the whole belief base parsed into rdflib cost half a second per shape (#711).
_SHAPE_GRAPHS_Q = """
SELECT DISTINCT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind . FILTER(isIRI(?g))
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } }
ORDER BY ?g"""


def judge_desires(store: ox.Store) -> None:
    """Judge every desire the store holds at the present and at every instant its holder
    foresees, and write the judgments to the store — the first of the road's two functions
    (judge-desires-then-derive-wants). After it, the store says what each desire's met-test
    read: met or unmet, and where unmet the results, one `deliberation:Judgment` per desire
    per instant in the holder's judgment graph, replaced whole. Nothing of this run is kept
    anywhere else — no object comes back — so `derive_wants` reads the store and nothing in hand.

    A FUNCTION OVER THE ENGINE. It is handed `pyoxigraph.Store` and no wrapper, collection or
    agent: the desires and who holds them are asked of the graphs of desires, the instants of
    the predictions' periods, the dataset at each instant of the catalogue — the texts above,
    each naming what it reads — and the judgments are written per holder. One agent, one
    volume, so the holder is the agent; a store holding several agents' desires is judged
    for each, over what each holds and what nobody does. The one thing not in the store is
    the present, which is the clock's (the-agent-keeps-one-timeline-and-its-clock-may-run-fast).

    ONE SELECT PER DESIRE PER INSTANT, and not one union of them: the compiler measured a
    single UNION of every shape at thirteen times the cost of the selects asked one by one,
    so this iterates where the contract is the whole. The foreseen instants are every
    prediction's start, where the dataset holds the prediction beside the present (#643).
    A desire whose met-test the compiler refuses is not judged, and the log says so: it was
    judged by the choir once, and a function over the store has no choir to ask — nor a
    shipped desire whose met-test is refused.
    """
    now = clock.now()
    shapes = shapes_in(store)
    by_holder: dict[str, list[tuple[str, str | None]]] = {}
    for row in store.query(bind(_ROOTS_Q, now=instant(now)), prefixes=NAMESPACES):
        by_holder.setdefault(row["holder"].value, []).append(
            (row["desire"].value, row["shape"].value if row["shape"] is not None else None))
    for holder, roots in by_holder.items():
        starts = _starts(store, holder)
        judged: list[tuple[str, datetime | None, bool, list[dict]]] = []
        for root, shape in roots:
            select = _compiled(shapes, shape, root)
            if select is None:
                continue
            for at in [None, *starts]:
                rows = _violations(store, select, holder, at or now, now)
                if rows is None:
                    log.error("%s: could not be judged at %s", root.rsplit("#", 1)[-1], at or "now")
                    continue
                judged.append((root, at, not rows, rows))
        save_judgments(store, holder, judged)


def shapes_in(store: ox.Store) -> rdflib.Graph:
    """Every graph of desires and of wants, parsed once — where a root's shape lives with its
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


def _compiled(shapes: rdflib.Graph, shape: str | None, root: str) -> str | None:
    """`shape` compiled to its report select out of `shapes`, or None — and a word in the log
    — where the root states none or the compiler refuses it."""
    from orexis_agent_progression.violation import Unsupported, report_select

    if shape is None:
        return None
    try:
        return report_select(shapes.cbd(rdflib.URIRef(shape)), rdflib.URIRef(shape))
    except Unsupported as exc:
        log.warning("%s: its met-test cannot be compiled, so it is not judged: %s",
                    root.rsplit("#", 1)[-1], exc)
        return None


def _starts(store: ox.Store, holder: str) -> list[datetime]:
    return [datetime.fromisoformat(row["start"].value)
            for row in store.query(bind(_STARTS_Q, holder=holder), prefixes=NAMESPACES)]


def _violations(store: ox.Store, select: str, holder: str, at: datetime,
                now: datetime) -> list[dict] | None:
    """The select's rows over the graphs `holder`'s desire is judged over at `at`, each a
    dict of the engine's own terms by variable name, one per distinct row — two predictions
    holding at one instant give one node two offending values, and both are told. None where
    the engine refuses the text."""
    graphs = [ox.NamedNode(g) for g in graphs_holding(store, FORESEEN, holder=holder, at=at, now=now)]
    try:
        answer = store.query(select, prefixes=NAMESPACES, default_graph=graphs)
        names = [v.value for v in answer.variables]
        rows: dict[tuple, dict] = {}
        for solution in answer:
            row = {name: solution[name] for name in names if solution[name] is not None}
            rows.setdefault(tuple(sorted((k, str(v)) for k, v in row.items())), row)
    except Exception as exc:                                        # noqa: BLE001
        log.error("the met-test could not be read at %s: %s", at, exc)
        return None
    return [rows[key] for key in sorted(rows)]

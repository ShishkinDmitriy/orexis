"""`says`: what taking a step tells a peer, as documents, made from the present.

An action whose taking tells somebody something has an `execution:Saying` among its operations,
an `sh:construct` over the beliefs as they stand when the step is taken, with the step's
parameters as `$tokens`, `$me` and `$now`. Its result is read as documents, the shape a world's files and a peer's messages
share: an IRI the result says is `execution:to` an agent is a graph, what is said of it and of
the blank nodes hanging off it is its content, and its kind, its period and whom it is to are
the rows about it — `rdf:type` of a class the vocabulary puts beneath `orexis:Graph`,
`dcterms:temporal`, `execution:to`. A round is a graph named for the round, a claim one named
for the claim, so a document is whatever one thing it is about. Execution names no transport:
the container believes each document as said and hands it to whoever reaches its agents.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent import clock
from agent.ontology import ACTION, KNOWN, OREXIS, local_of
from agent.store import bind, closed, construct, graphs_of, instant, rows

from .implementation import SAYING, operations
from .ontology import EXECUTION

log = logging.getLogger("says")

_TAKES_Q = """SELECT ?takes WHERE { $action orexis:takes ?takes }"""

_TO = EXECUTION + "to"
_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_TEMPORAL = "http://purl.org/dc/terms/temporal"
_GRAPH = OREXIS + "Graph"


def says(store, said: dict, me: str, *, order: float | None = None) -> list[tuple[list[str], ox.Store]]:
    """Every document the step `said` tells, with the agents it is to — the executor's rows for
    the step, keyed by local part as `Executor.step_of` answers them — made over the beliefs
    holding now: every saying of the action's implementation, or those of one `order`. Empty
    where it has none or its texts construct no graph."""
    action = said.get("fills")
    if not action:
        return []
    texts = [op.text for op in operations(store, action)
             if op.kind == SAYING and op.text and (order is None or op.order == order)]
    if not texts:
        return []
    now = clock.now()
    tokens = {"me": me, "now": instant(now)}
    for r in rows(store, _TAKES_Q, graphs_of(store, ACTION), action=action):
        if local_of(r["takes"]) in said:
            tokens[local_of(r["takes"])] = said[local_of(r["takes"])]
    triples: list = []
    for text in texts:
        triples += construct(store, bind(text, **tokens), graphs_of(store, *KNOWN, at=now, now=now))
    return _documents(store, triples, action)


def _documents(store, triples, action: str) -> list[tuple[list[str], ox.Store]]:
    """The result read as documents: one per IRI said to be `execution:to` somebody."""
    to: dict = {}
    for t in triples:
        if t.predicate.value == _TO and isinstance(t.subject, ox.NamedNode):
            to.setdefault(t.subject, set()).add(t.object.value)
    out, used = [], set()
    for graph, agents in sorted(to.items(), key=lambda kv: kv[0].value):
        doc = ox.Store()
        mine, frontier = set(), {graph}
        while frontier:
            here = [t for t in triples if t.subject in frontier and t not in mine]
            mine |= set(here)
            frontier = {t.object for t in here if isinstance(t.object, ox.BlankNode)}
        about_graph = {t for t in mine if t.subject == graph and (
            t.predicate.value in (_TO, _TEMPORAL)
            or (t.predicate.value == _TYPE and _GRAPH in closed(store, t.object.value)))}
        rows_, frontier = set(about_graph), {t.object for t in about_graph if isinstance(t.object, ox.BlankNode)}
        while frontier:
            here = {t for t in mine if t.subject in frontier}
            rows_ |= here
            frontier = {t.object for t in here if isinstance(t.object, ox.BlankNode)}
        for t in mine:
            if t.predicate.value == _TO:
                continue
            doc.add(ox.Quad(t.subject, t.predicate, t.object, ox.DefaultGraph() if t in rows_ else graph))
        used |= mine
        out.append((sorted(agents), doc))
    stray = [t for t in triples if t not in used]
    if stray:
        log.warning("%s says %d fact(s) about no graph it is to anyone: %s", local_of(action), len(stray),
                    ", ".join(sorted({local_of(t.subject.value) for t in stray if isinstance(t.subject, ox.NamedNode)})))
    return out

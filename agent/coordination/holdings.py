"""`holdings`: what an agent says of its own future under one constraint — the values its walking plans give
the things it acts for on the constraint's key, each over the period it holds
(knowledge/domain/coordination/holding.md).

**THE KEY IS READ OFF THE CONSTRAINT.** A constraint's select joins two subjects on the values of some of
their predicates — the courier's two vans on their column and their row — and those predicates are its
key: what two agents can both want. Read by parsing the text, never by naming a domain's word, so any
constraint over a key two things can share is a resource here.

**A HOLDING IS READ OFF THE INTENTIONS.** For each thing the agent acts for, the values it holds now, then
each step of a walking intention, in order, whose predicted change (`execution:adds`) gives the thing new
values on the key: the old values hold until the step's latest landing, the new from its earliest, and
the last hold on. Nothing else of a plan is read, and nothing is said where no step changes the key: an
agent that is not going anywhere asks nothing, and what stands still is what sensing sees.
"""

from __future__ import annotations

from datetime import datetime
from functools import cache
from typing import NamedTuple

import pyoxigraph as ox
from rdflib.plugins.sparql import parser as sparql_parser
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.term import URIRef, Variable

from agent.ontology import BELIEF, FORECAST, SELF_GRAPH
from agent.store import PREFIXES, graphs_of, rows

from .ontology import COMMITTED_STEP_GRAPH, CONSTRAINT_GRAPH

_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


class Holding(NamedTuple):
    """One thing's values on a constraint's key, over a period: `start` None where the thing holds them now,
    since whenever it came to, and `end` None where nothing ends them."""
    thing: str
    values: tuple[tuple[str, ox.Term], ...]
    start: datetime | None
    end: datetime | None

    def overlaps(self, other: "Holding") -> bool:
        """Whether two holdings hold the same values of the key over periods that overlap."""
        return (self.values == other.values
                and (other.end is None or self.start is None or self.start < other.end)
                and (self.end is None or other.start is None or other.start < self.end))


#  WHAT A CONSTRAINT SAYS IS UNMET OR MET: the select under either polarity, the avoided state's or a shape's.
_TEXTS_Q = """
SELECT ?text WHERE {
  { $constraint planning:unmetWhen ?s . ?s sh:select ?text }
  UNION { $constraint planning:metWhen ?shape . ?shape sh:sparql ?c . ?c sh:select ?text } }"""
#  THE THINGS THE AGENT ACTS FOR.
_THINGS_Q = "SELECT ?t WHERE { ?me a orexis:Self ; orexis:actsFor ?t } ORDER BY ?t"
_VALUES_Q = "SELECT ?p ?v WHERE { $thing ?p ?v }"
#  EVERY STANDING INTENTION, the plan it adopts and the step it stands at; and whether it ends after it.
_STANDING_Q = """
SELECT ?plan ?step ?ending WHERE { GRAPH ?g { ?i a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
  FILTER NOT EXISTS { ?i execution:resolvedAt ?done } OPTIONAL { ?i execution:endsAfter ?ending } } }"""
#  A PLAN'S STEPS: each, the one after it, the graph naming what it adds, and the two ends of its landing.
_STEPS_Q = """
SELECT ?step ?next ?adds ?lands ?latest WHERE { GRAPH $plan { ?step a execution:Step .
  OPTIONAL { ?step execution:then ?next } OPTIONAL { ?step execution:adds ?adds }
  OPTIONAL { ?step execution:landsAt ?lands } OPTIONAL { ?step execution:notAfter ?latest } } }"""


def holdings(store: ox.Store, constraint: str, at: datetime) -> list[Holding]:
    """Every holding of the things the self of `store` acts for under `constraint`, standing at `at`: for
    each thing, its values now and each change its walking plans make to them, in order. None where the
    constraint joins on no key, or no step of a walking plan changes a thing's values on it."""
    key = _key_of(store, constraint)
    if not key:
        return []
    things = [r["t"] for r in rows(store, _THINGS_Q, [*graphs_of(store, BELIEF, common=True), *graphs_of(store, SELF_GRAPH)])]
    present = _present(store, at)
    changes = _changes(store, things, key)
    out: list[Holding] = []
    for thing in things:
        now = {r["p"]: _term(store, thing, r["p"], present) for r in rows(store, _VALUES_Q, present, thing=thing) if r["p"] in key}
        steps = changes.get(thing, [])
        if set(now) != key or not steps:
            continue
        values, start = dict(now), None
        for lands, latest, change in steps:
            out.append(Holding(thing, _tuple(values), start, latest or lands))
            values.update(change)
            start = lands
        out.append(Holding(thing, _tuple(values), start, None))
    return out


def _key_of(store: ox.Store, constraint: str) -> frozenset[str]:
    """The predicates `constraint` joins two subjects on: every predicate whose object is a variable
    some other subject's pattern also ends in. Empty where its text will not parse or joins nothing."""
    texts = [r["text"] for r in rows(store, _TEXTS_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *graphs_of(store, BELIEF, common=True)],
                                     constraint=constraint)]
    return frozenset().union(*(_key(text) for text in texts)) if texts else frozenset()


@cache
def _key(text: str) -> frozenset[str]:
    try:
        algebra = translateQuery(sparql_parser.parseQuery(PREFIXES + text)).algebra
    except Exception:                                                   # noqa: BLE001 — a text that will not parse joins nothing
        return frozenset()
    triples: list = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if getattr(node, "name", None) == "BGP":
                triples.extend(node.get("triples", []))
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
    walk(algebra)
    subjects: dict = {}
    for s, p, o in triples:
        if isinstance(p, URIRef) and str(p) != _TYPE and isinstance(o, Variable):
            subjects.setdefault(o, set()).add(s)
    return frozenset(str(p) for s, p, o in triples
                     if isinstance(p, URIRef) and str(p) != _TYPE and isinstance(o, Variable) and len(subjects[o]) > 1)


def _present(store: ox.Store, at: datetime) -> list[str]:
    """What the agent believes holds at `at`: every belief holding then, save its self graph, a forecast and a
    committed step, which say what the agent is and what will hold."""
    aside = set(graphs_of(store, SELF_GRAPH, FORECAST, COMMITTED_STEP_GRAPH))
    return [g for g in graphs_of(store, BELIEF, at=at) if g not in aside]


def _term(store: ox.Store, thing: str, predicate: str, graphs: list[str]) -> ox.Term:
    """The value `thing` holds on `predicate` now, as the term it is — the engine's, so two agents' values
    compare as terms and not as their spellings."""
    for graph in graphs:
        for q in store.quads_for_pattern(ox.NamedNode(thing), ox.NamedNode(predicate), None, ox.NamedNode(graph)):
            return q.object
    raise LookupError(f"{thing} holds nothing on {predicate}")


def _changes(store: ox.Store, things: list[str], key: frozenset[str]) -> dict[str, list]:
    """Per thing, every change a walking plan's steps make to its values on the key, in the order they are
    walked: (earliest landing, latest landing, {predicate: value})."""
    out: dict[str, list] = {}
    for r in rows(store, _STANDING_Q, ()):
        chain = {s["step"]: s for s in rows(store, _STEPS_Q, (), plan=r["plan"])}
        step = r["step"]
        while step in chain:
            s = chain[step]
            for thing in things:
                change = {q.predicate.value: q.object for q in store.quads_for_pattern(ox.NamedNode(thing), None, None, ox.NamedNode(s["adds"]))
                          if q.predicate.value in key} if s.get("adds") else {}
                if change:
                    out.setdefault(thing, []).append((_at(s.get("lands")), _at(s.get("latest")), change))
            step = None if r.get("ending") else s.get("next")
    for changes in out.values():
        changes.sort(key=lambda c: c[0] or datetime.min)
    return out


def _at(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def _tuple(values: dict) -> tuple:
    return tuple(sorted(values.items()))


#  ─── holdings in what is said: one shape, written by `ask` and `answer`, read by both and by `lay` ───

_COORDINATION = "http://example.org/orexis/coordination#"
_XSD_DATETIME = ox.NamedNode("http://www.w3.org/2001/XMLSchema#dateTime")
_OF, _FROM, _UNTIL, _HOLDING = (ox.NamedNode(_COORDINATION + w) for w in ("of", "from", "until", "holding"))
_TEMPORAL = ox.NamedNode("http://purl.org/dc/terms/temporal")
_START, _END = ox.NamedNode("http://example.org/orexis#start"), ox.NamedNode("http://example.org/orexis#end")
_HOLDINGS_Q = """
SELECT ?h ?t ?p ?v ?from ?until WHERE { GRAPH $graph { ?n coordination:holding ?h . ?h coordination:of ?t ; ?p ?v .
  OPTIONAL { ?h coordination:from ?from } OPTIONAL { ?h coordination:until ?until } } }"""


def _said(graph: str, kind: str, node: str, about: list[tuple[str, ox.Term]], held: list[Holding],
          period: tuple[datetime, datetime] | None = None) -> ox.Store:
    """A document of one graph, `graph`, of `kind`: the node `node` with what `about` says of it, and each
    holding of `held` hanging off it — the thing, the values on the key with the key's own predicates, and
    the period; and the graph's own period, where `period` gives one."""
    doc, g = ox.Store(), ox.NamedNode(graph)
    doc.add(ox.Quad(g, ox.NamedNode(_TYPE), ox.NamedNode(kind), ox.DefaultGraph()))
    if period is not None:
        p = ox.BlankNode()
        doc.add(ox.Quad(g, _TEMPORAL, p, ox.DefaultGraph()))
        doc.add(ox.Quad(p, _START, ox.Literal(period[0].isoformat(), datatype=_XSD_DATETIME), ox.DefaultGraph()))
        doc.add(ox.Quad(p, _END, ox.Literal(period[1].isoformat(), datatype=_XSD_DATETIME), ox.DefaultGraph()))
    n = ox.NamedNode(node)
    for predicate, value in about:
        doc.add(ox.Quad(n, ox.NamedNode(predicate), value, g))
    for i, h in enumerate(held):
        hn = ox.NamedNode(f"{node}/holding/{i}")
        doc.add(ox.Quad(n, _HOLDING, hn, g))
        doc.add(ox.Quad(hn, ox.NamedNode(_TYPE), ox.NamedNode(_COORDINATION + "Holding"), g))
        doc.add(ox.Quad(hn, _OF, ox.NamedNode(h.thing), g))
        for predicate, value in h.values:
            doc.add(ox.Quad(hn, ox.NamedNode(predicate), value, g))
        if h.start is not None:
            doc.add(ox.Quad(hn, _FROM, ox.Literal(h.start.isoformat(), datatype=_XSD_DATETIME), g))
        if h.end is not None:
            doc.add(ox.Quad(hn, _UNTIL, ox.Literal(h.end.isoformat(), datatype=_XSD_DATETIME), g))
    return doc


def _heard(store: ox.Store, graph: str) -> list[Holding]:
    """The holdings a question or an answer in `graph` carries, as the terms they were said in."""
    found: dict[str, dict] = {}
    for r in rows(store, _HOLDINGS_Q, (), graph=graph):
        h = found.setdefault(r["h"], {"thing": r["t"], "from": r.get("from"), "until": r.get("until")})
        if r["p"] not in (_TYPE, _OF.value, _FROM.value, _UNTIL.value):
            h.setdefault("p", set()).add(r["p"])
    out = []
    for node, h in sorted(found.items()):
        values = tuple(sorted((p, next(q.object for q in store.quads_for_pattern(ox.NamedNode(node), ox.NamedNode(p), None, ox.NamedNode(graph))))
                              for p in h.get("p", ())))
        out.append(Holding(h["thing"], values, _at(h.get("from")), _at(h.get("until"))))
    return out


#  ─── whether two holdings want one resource: the constraint's own word, asked of the two at once ───

_KINDS_Q = "SELECT ?k WHERE { $thing a ?k }"


def _violates(store: ox.Store, constraint: str, mine: Holding, theirs: Holding) -> bool:
    """Whether `constraint` reads a violation where `mine` and `theirs` hold at once: its own select, asked of
    the two things with the kinds the agent believes them of and the values the holdings give them, and nothing
    else. Two vans at one position violate the courier's *no two vans at one position* and not its *no van on
    an obstacle*, which a key alone cannot tell apart."""
    if not mine.overlaps(theirs):
        return False
    scratch = ox.Store()
    common = graphs_of(store, BELIEF, common=True)
    for h in (mine, theirs):
        node = ox.NamedNode(h.thing)
        for r in rows(store, _KINDS_Q, common, thing=h.thing):
            scratch.add(ox.Quad(node, ox.NamedNode(_TYPE), ox.NamedNode(r["k"]), ox.DefaultGraph()))
        for predicate, value in h.values:
            scratch.add(ox.Quad(node, ox.NamedNode(predicate), value, ox.DefaultGraph()))
    for r in rows(store, _TEXTS_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *common], constraint=constraint):
        try:
            if list(scratch.query(PREFIXES + r["text"])):
                return True
        except (SyntaxError, ValueError):
            return True                          # a text that will not run cannot be shown not to collide
    return False

"""What the vocabulary entails of the nodes in one graph, asserted there: membership under
every class the domain DEFINES as an intersection — a named class, values pinned by
`owl:hasValue`, a value held inside a datatype restriction's facets — and the families each
such class sits beneath.

**DELIBERATION IS ON TRIPLES, AND A NUMBER IS NOT SPECIAL** (#576). What a reading of a
property can BE is decided inside the domain, as classes of observations — a reading below
the region its subject states is a `sensing:BelowRegion`, one inside an `InRegion` — and the
member class per (subject, property) is minted from the range the world states, as an
`owl:intersectionOf` the observation class, the subject and the property by `owl:hasValue`,
and the result by a datatype restriction. This is the one evaluator of those definitions: it
reads them as data off public knowledge and asserts exactly what the OWL says, so a step's
precondition and a desire's met-test say the side as a triple and an outside reasoner would
agree. The side is what the mind reads; the number it was drawn from is the instrument's
word and stays where the instrument put it.

**A FUNCTION OVER THE ENGINE**, handed the store and the graph to write into — and, where the
node's facts are spread over two graphs, the graphs to read them from: the sensing layer
keeps a reading's key and its sides in one graph and its number in another, so the number is
read from the second and the side written into the first. It was `Store.entail`, a method
on the wrapper that held the engine, reading the definitions through a memo the wrapper
dropped on every write; the definitions are a fact only a write to public knowledge can
change, so the memo is the caller's (`Memo`), as every other such answer's is.

**THE SIDES STOP AT THE BASE.** A member side's ancestors are its family
(`sensing:BelowRegion`) and then whatever sits above `sosa:Observation`; the node was typed
`sosa:Observation` already, and what THAT class is beneath is the closure's business at genesis
and never a fact a reading gained by being classified. So every side the node carries — one
entailed here, or one a drift's rule typed it with — brings its ancestors up to, and not
including, a class some definition intersects; a rule that types the member alone leaves the
family to this, and a shape asking `sh:class sensing:BelowRegion` reads either alike.
"""

from __future__ import annotations

import pyoxigraph as ox

from .ontology import PUBLIC
from .store import graphs_of, remember, rows

_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  EVERY DEFINITION THE VOCABULARY STATES, one row per PART of an intersection, of three
#  kinds: a named class the node must be (`?base`); a property the definition FIXES to one
#  value with `owl:hasValue` (`?fixedProperty`, and the value as `?fixedIri` where it is an
#  IRI or `?fixedText` where it is a literal — two columns, since one variable cannot say
#  which kind of term came back); and a datatype restriction, the property it holds a value
#  of (`?facetProperty`) with each `?facet` and its `?bound`.
_DEFINITIONS_Q = """
SELECT ?cls ?base ?fixedProperty ?fixedIri ?fixedText ?facetProperty ?facet ?bound WHERE {
  { ?cls owl:equivalentClass/owl:intersectionOf ?list .
    ?list rdf:rest*/rdf:first ?base . FILTER(isIRI(?base)) }
  UNION
  { ?cls owl:equivalentClass/owl:intersectionOf ?list .
    ?list rdf:rest*/rdf:first ?part .
    ?part owl:onProperty ?fixedProperty ; owl:hasValue ?fixed .
    BIND(IF(isIRI(?fixed), STR(?fixed), "") AS ?fixedIri)
    BIND(IF(isIRI(?fixed), "", STR(?fixed)) AS ?fixedText) }
  UNION
  { ?cls owl:equivalentClass/owl:intersectionOf ?list .
    ?list rdf:rest*/rdf:first ?part .
    ?part owl:onProperty ?facetProperty ; owl:someValuesFrom/owl:withRestrictions ?facets .
    ?facets rdf:rest*/rdf:first ?f . ?f ?facet ?bound . FILTER(?facet != rdf:type) }
}"""

#  WHAT EVERY CLASS IS BENEATH. One `rdfs:subClassOf` step is every step where the closure
#  is materialised; a case written by hand may not have it, so the path is walked here.
_SUPERS_Q = """
SELECT ?c ?s WHERE { ?c rdfs:subClassOf+ ?s . FILTER(isIRI(?s) && isIRI(?c)) }"""


def entail(store, graph: str, *, of=(), read=(), memo=None) -> list[tuple]:
    """Assert in `graph` what the vocabulary entails of the nodes there, and answer with the
    memberships asserted, as `(node, class)` pairs of engine terms.

    `of` narrows the question to some nodes — the reading just written — as IRIs or terms;
    given none, every typed node in `graph` is asked. `read` names the graphs a node's facts
    are gathered from, `graph` alone where none is given: a node whose key is in one graph
    and whose number is in another is judged over both and classified in the first.

    Asserted through the term API and never an INSERT, since a blank node written back as
    text is a new blank node.
    """
    into = ox.NamedNode(graph)
    sources = [ox.NamedNode(g) for g in (read or (graph,))]
    nodes = [ox.NamedNode(x) if isinstance(x, str) else x for x in of] or _typed_in(store, into)
    defs, supers = remember(memo, ("definitions",), lambda: _definitions(store))
    out = []
    for node in nodes:
        values: dict = {}
        types: set = set()
        for source in sources:
            for q in store.quads_for_pattern(node, None, None, source):
                if q.predicate == _RDF_TYPE:
                    types.add(q.object)
                values.setdefault(q.predicate, set()).add(q.object)
        for cls, (bases, fixed, ranges) in defs.items():
            if cls in types or not bases <= types:
                continue
            if any(v not in values.get(p, ()) for p, v in fixed):
                continue
            if all(_within(values.get(p, ()), facets) for p, facets in ranges):
                out.append((node, cls))
                types.add(cls)
        #  AND THE SIDES: every class the node is typed with, closed upward — the member a
        #  rule typed it with as much as one entailed here — stopping at a BASE, a class some
        #  definition intersects, and at everything above one: a reading gains its sides'
        #  families and never what sits above `sosa:Observation`.
        rooted = types & bases_of(defs)
        stop = {s for t in rooted for s in supers.get(t, ())} | rooted
        for cls in sorted(types - rooted, key=lambda c: c.value):
            for sup in sorted(supers.get(cls, ()), key=lambda c: c.value):
                if sup not in types and sup not in stop:
                    out.append((node, sup))
                    types.add(sup)
    for node, cls in out:
        store.add(ox.Quad(node, _RDF_TYPE, cls, into))
    return out


def bases_of(defs: dict) -> frozenset:
    """The named classes the definitions intersect — what a defined class is a kind OF."""
    return frozenset(b for bases, _, _ in defs.values() for b in bases)


def _typed_in(store, graph: ox.NamedNode) -> list:
    seen: list = []
    for q in store.quads_for_pattern(None, _RDF_TYPE, None, graph):
        if q.subject not in seen:
            seen.append(q.subject)
    return seen


def _definitions(store) -> tuple[dict, dict]:
    """The domain's class definitions off public knowledge — class to (the named classes it
    intersects, the values it fixes, the ranges it holds a value to) — and every class's
    ancestors."""
    public = graphs_of(store, PUBLIC)
    defs: dict = {}
    for r in rows(store, _DEFINITIONS_Q, public):
        cls = ox.NamedNode(r["cls"])
        bases, fixed, ranges = defs.setdefault(cls, (set(), set(), {}))
        if r.get("base"):
            bases.add(ox.NamedNode(r["base"]))
        if r.get("fixedProperty"):
            fixed.add((ox.NamedNode(r["fixedProperty"]),
                        ox.NamedNode(r["fixedIri"]) if r.get("fixedIri") else ox.Literal(r.get("fixedText", ""))))
        if r.get("facetProperty") and r.get("facet"):
            ranges.setdefault(ox.NamedNode(r["facetProperty"]), []).append(
                (r["facet"].rsplit("#", 1)[-1], float(r["bound"])))
    closed = {c: (b, p, tuple((k, tuple(v)) for k, v in r.items())) for c, (b, p, r) in defs.items()}
    supers: dict = {}
    for r in rows(store, _SUPERS_Q, public):
        supers.setdefault(ox.NamedNode(r["c"]), set()).add(ox.NamedNode(r["s"]))
    return closed, supers


def _within(values, facets) -> bool:
    """Does some value satisfy every facet of a datatype restriction? Numeric, as XSD reads
    them; a value that is not a number satisfies nothing, and no value at all is not within."""
    for v in values:
        try:
            n = float(v.value)
        except (AttributeError, TypeError, ValueError):
            continue
        if all((n < b if f == "maxExclusive" else n <= b if f == "maxInclusive" else
                n > b if f == "minExclusive" else n >= b if f == "minInclusive" else True)
               for f, b in facets):
            return True
    return False

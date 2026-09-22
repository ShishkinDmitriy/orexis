"""What each action and each derivation TOUCHES, read off its own texts.

Two sets per action, both derived and neither declared (#488):

- what it WRITES — the predicates of its `sh:construct` template and its `orexis:retracts`;
- what it READS — the predicates of its `orexis:available` precondition.

A derivation rule is the same pair read off one INSERT: its template writes, its WHERE reads.
Nothing here is declared — a stated `orexis:touches` would be a second statement of what the
construct already settles — and nothing is stored: computed per call, parsed once per text.

ANYTHING UNREADABLE READS AS `ANYTHING`: a body the parser refuses, a template with a variable
predicate. Over-approximation is safe wherever these sets are used and under-approximation is
not, which is why the unreadable case is a value rather than an error.

**AND WHAT A WANT READS**, off its met-test: every predicate its paths navigate and its
`sh:sparql` constraints mention. That is the question "which words is this want in play over",
answered by reading the shape rather than by a property somebody declared beside it — which is
the whole point, since a declared one narrows the planning problem before the planner has seen
it. A want whose shape the walker cannot read reads as ANYTHING and is in play over
everything, which is the safe direction.

**TWO KINDS OF FUNCTION, TOLD APART BY WHAT THEY ARE HANDED.** Over the STORE:
`actions_of(store)` and `stored_edges(store, graphs)`, which read what the store holds and
answer for every action and every derivation in it. Over a TEXT or a parsed shape:
`parseable`, `reads_of_select`, `writes_of_construct`, `reads_of_shape`, which own nothing and
ask nothing — hand one a string and it answers. The store-facing pair is written the way
everything else here is (a-function-over-the-store-is-handed-the-engine): `actions_of` took a
QUERY, a lambda closing over the store and the graphs to read, which is the caller deciding
what this reads and this deciding nothing.

**WHAT THIS ANSWERS FOR IS THE SCOPES.** `scope_actions` clusters the vocabulary by which
predicates move together, and a want belongs to the scope of what it reads. It returns with the thing that needs it (an-agent-is-four-things).
"""

from __future__ import annotations

from datetime import datetime

import functools
import logging
import re

import rdflib
from rdflib import RDF, URIRef
from rdflib.collection import Collection
from rdflib.paths import AlternativePath, InvPath, MulPath, NegatedPath, SequencePath
from rdflib.plugins.sparql.algebra import translateQuery, traverse
from rdflib.plugins.sparql.parser import parseQuery

#  WHAT A `$token` IS, from the module that BINDS one. It was spelled here too, a
#  character apart, which is two definitions of one thing waiting to disagree.
from orexis.agent import clock
from orexis.agent.ontology import PUBLIC
from orexis.agent.store import _TOKEN, PREFIXES, graphs_of, rows

log = logging.getLogger("touches")

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
ANYTHING = None          # the set that contains every predicate: unreadable, so unfiltered

#  The tokens a rule text takes, each replaced with something that PARSES — a variable where
#  the token is a term, a row where it is a VALUES block, nothing where it is a USING list.
#  Parsing is all this is for: nothing is run, so the values are never right, only well-formed.
_PARSE_TOKENS = {
    "$given": "", "$derived": "<urn:parse:derived>", "$evidence": "<urn:parse:evidence>",
    "$wants": "(<urn:parse:want> <urn:parse:about>)", "$properties": "<urn:parse:property>",
    "$litres": "1.0", "$this": "?this",
}
_INTO = re.compile(r"\$into\([^)]*\)")


def parseable(text: str) -> str:
    """The text with every `$token` made parseable — see `_PARSE_TOKENS`."""
    text = _INTO.sub("<urn:parse:into>", text)
    for token, stand_in in _PARSE_TOKENS.items():
        text = text.replace(token, stand_in)
    return _TOKEN.sub(lambda m: "?" + m.group(1), text)


# --- predicates of a text ----------------------------------------------------------------------

def _path_iris(p) -> set | None:
    if isinstance(p, URIRef):
        return {p}
    if isinstance(p, (MulPath, InvPath)):
        return _path_iris(p.path if isinstance(p, MulPath) else p.arg)
    if isinstance(p, (SequencePath, AlternativePath)):
        out = set()
        for a in p.args:
            part = _path_iris(a)
            if part is None:
                return ANYTHING
            out |= part
        return out
    if isinstance(p, NegatedPath):
        return ANYTHING                                  # "anything but" is anything
    return ANYTHING                                      # a variable predicate


def _predicates_in(node, out: set) -> bool:
    """Collect the predicates of every triple pattern under `node`; False if any is unreadable."""
    ok = [True]

    def visit(n):
        if getattr(n, "name", None) == "BGP":
            for _, p, _ in n["triples"]:
                iris = _path_iris(p)
                if iris is None:
                    ok[0] = False
                else:
                    out.update(iris)
        elif getattr(n, "name", None) == "TriplesBlock":
            #  A pattern under EXISTS / NOT EXISTS is READ as much as one in the group — a
            #  want saying "unmet while this fact is absent" reads that fact's predicate —
            #  and rdflib leaves it UNTRANSLATED inside the filter's expression: a parse-tree
            #  TriplesBlock rather than a BGP (#523: a promise's want is exactly that shape,
            #  and read nothing before this).
            for triple in n["triples"]:
                iris = _path_iris(triple[1]) if len(triple) == 3 else None
                if iris is None:
                    ok[0] = False
                else:
                    out.update(iris)
        return n
    traverse(node, visitPost=visit)
    return ok[0]


@functools.lru_cache(maxsize=512)


@functools.lru_cache(maxsize=512)
def reads_of_select(text: str) -> frozenset | None:
    """The predicates a SELECT's or a CONSTRUCT's WHERE reads, or ANYTHING if unparseable."""
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001 — unreadable is a finding
        log.debug("could not parse a query for the predicates it reads: %s", exc)
        return ANYTHING
    out: set = set()
    where = alg.get("p", alg)
    return frozenset(out) if _predicates_in(where, out) else ANYTHING


@functools.lru_cache(maxsize=512)
def reads_of_shape(shapes: rdflib.Graph, shape) -> frozenset | None:
    """Every predicate a shape's paths and SPARQL constraints read, or ANYTHING."""
    out: set = set()
    for prop in shapes.objects(shape, SH.property):
        iris = _shacl_path_iris(shapes, shapes.value(prop, SH.path))
        if iris is None:
            return ANYTHING
        out |= iris
        for p, o in shapes.predicate_objects(prop):
            if p == SH.equals:
                out.add(o)
            if p == SH.qualifiedValueShape:
                inner = reads_of_shape(shapes, o)
                if inner is None:
                    return ANYTHING
                out |= inner
    for constraint in shapes.objects(shape, SH.sparql):
        inner = reads_of_select(str(shapes.value(constraint, SH.select) or ""))
        if inner is None:
            return ANYTHING
        out |= inner
    for negated in shapes.objects(shape, SH["not"]):
        inner = reads_of_shape(shapes, negated)
        if inner is None:
            return ANYTHING
        out |= inner
    for p in (SH.targetSubjectsOf, SH.targetObjectsOf):
        out |= set(shapes.objects(shape, p))
    if (shape, SH.targetClass, None) in shapes:
        out.add(RDF.type)
    return frozenset(out)

def _shacl_path_iris(g: rdflib.Graph, node) -> set | None:
    if node is None:
        return ANYTHING
    if isinstance(node, URIRef):
        return {node}
    if (node, RDF.first, None) in g:
        out = set()
        for part in Collection(g, node):
            iris = _shacl_path_iris(g, part)
            if iris is None:
                return ANYTHING
            out |= iris
        return out
    for pred in (SH.inversePath, SH.oneOrMorePath, SH.zeroOrMorePath, SH.zeroOrOnePath):
        inner = g.value(node, pred)
        if inner is not None:
            return _shacl_path_iris(g, inner)
    alternatives = g.value(node, SH.alternativePath)
    if alternatives is not None:
        return _shacl_path_iris(g, alternatives)
    return ANYTHING


def writes_of_construct(text: str) -> frozenset | None:
    """The predicates a CONSTRUCT's template writes, or ANYTHING if unparseable or variable."""
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001
        log.debug("could not parse a construct for the predicates it writes: %s", exc)
        return ANYTHING
    out = set()
    for _, p, _ in alg.get("template") or ():
        if not isinstance(p, URIRef):
            return ANYTHING
        out.add(p)
    return frozenset(out)


# --- what each action and each derivation touches -----------------------------------------------

_ACTIONS_Q = """
SELECT ?action ?available ?construct ?retracts WHERE {
  ?action a orexis:Action .
  OPTIONAL { ?action orexis:available ?available }
  OPTIONAL { ?action sh:construct ?construct }
  OPTIONAL { ?action orexis:retracts ?retracts }
}"""

def actions_of(store, at: datetime | None = None) -> dict[str, tuple]:
    """Every action the store holds as `iri -> (reads, writes)`, each ANYTHING where unreadable.

    A FUNCTION OVER THE STORE, handed the engine and nothing else. It took a QUERY — a lambda
    closing over the store and the graphs to read — which is the caller deciding what this
    reads and this deciding nothing; the graphs an action is declared in are public knowledge,
    which is this module's to ask for, as `stored_edges` beside it already asks.
    """
    out = {}
    for row in rows(store, _ACTIONS_Q, graphs_of(store, PUBLIC, at=at or clock.now())):
        if not row.get("construct"):
            #  AN ACTION STATING NO EFFECT is an action an event adopts (#506) — never on a
            #  admitted by any world, never simulated — and has no place in a closure that
            #  simulated. Reading it as ANYTHING-writes-ANYTHING collapsed every want's
            #  closure to everything, for the market's Presenting.
            continue
        #  No precondition text is a lever with nothing to widen the want by — a world
        #  yields it no rows, but a construct it does carry says what it would write.
        reads = reads_of_select(row["available"]) if row.get("available") else frozenset()
        writes = writes_of_construct(row["construct"])
        if writes is not ANYTHING and row.get("retracts"):
            part = writes_of_construct(row["retracts"])
            if part is not ANYTHING:
                writes = frozenset(writes | part)
            elif not writes:
                #  A retract with a variable predicate and NO construct beside it removes
                #  something the text does not name: unreadable, and said so.
                writes = ANYTHING
            #  else: A RETRACT WITH A VARIABLE PREDICATE beside a construct — `?standing ?p
            #  ?o`, every shipped reading-replacing lever — removes the node the construct
            #  replaces, the readings graph's upsert, and so writes what the construct
            #  writes. Read as ANYTHING it made every such lever relevant to every want, and
            #  every want's view the whole world (#554, #565).
        out[row["action"]] = (reads, writes)
    return out


#  THE EDGES AS THE STORE HOLDS THEM: one `planning:Derivation` per INSERT, its sides as
#  predicates or as `planning:Anything`. Asked of the graphs of derivations by class.
_EDGES_Q = """
SELECT ?d ?reads ?writes WHERE {
  ?d a planning:Derivation .
  OPTIONAL { ?d planning:reads ?reads }
  OPTIONAL { ?d planning:writes ?writes } }"""


def stored_edges(store, graphs) -> tuple:
    """The derivations' (reads, writes) edges, read back from `graphs` — what genesis wrote
    from the rule files. A side saying `planning:Anything` is ANYTHING; a side saying
    nothing at all is empty, which is what a rule reading or writing no named predicate is."""
    from orexis.agent.store import rows

    from .ontology import ANYTHING as ANYTHING_IRI

    sides: dict = {}
    for row in rows(store, _EDGES_Q, graphs):
        reads, writes = sides.setdefault(row["d"], (set(), set()))
        for side, key in ((reads, "reads"), (writes, "writes")):
            if row.get(key):
                side.add(row[key])
    out = []
    for _name, (reads, writes) in sorted(sides.items()):
        out.append((ANYTHING if ANYTHING_IRI in reads else frozenset(URIRef(p) for p in reads),
                    ANYTHING if ANYTHING_IRI in writes else frozenset(URIRef(p) for p in writes)))
    return tuple(out)

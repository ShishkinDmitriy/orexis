"""Which levers could serve a want — read off the actions themselves, closed backward.

A pass simulates every row on the menu, and a row that names no want reaches every pass: a
courier pass simulates hanoi's moves, and one FREE foreign action that genuinely changes state
multiplied a three-disk solve 2.8 times (`knowledge/runbooks/measure-the-search.md`). Neither
the cost bound nor cycle detection can catch it, since a free action lets every descendant tie
and a world that really changed is somewhere new. What catches it is the question this module
answers: does this lever touch anything the want reads?

THREE SETS, ALL DERIVED, NONE DECLARED (#488):

- W, what the want READS — every `sh:path` on its shape, flattened to predicates, plus the
  predicates of any `sh:sparql` constraint or authored pattern, parsed;
- E, what an action WRITES — the predicates of its `sh:construct` template and its
  `orexis:retracts` template;
- P, what an action READS — the predicates of its `orexis:available`.

An action is relevant when E meets W; then W grows by its P, and again, to a fixed point.
THE CLOSURE IS WHAT KEEPS CHAINS ALIVE: a moisture want reads observation predicates, a dose
writes them, a dose's precondition reads a claim, a bid writes one — so the bid is relevant
on the second round, where filtering to actions that touch the goal would have deleted it.
A derivation rule is an edge in the same closure — its INSERT template writes, its WHERE
reads — with no row of its own: reasoning is saturation for the search and an edge for
relevance (the second ruling on #488). Sub-properties widen W the way the entailed graph
would, so an action writing the narrower word still meets a want reading the broader one.

OVER-APPROXIMATION IS SAFE AND UNDER-APPROXIMATION PRUNES A NEEDED STEP, which is the whole
design. Anything unreadable reads as ANYTHING: a `sh:sparql` body the parser refuses, an
effect text with a variable predicate, a want with no shape and no pattern — an obligation,
a call — and then every action stays. Predicates are a coarse key on purpose; two domains
sharing one stay mutually relevant, which costs forks and never correctness.

Nothing here is declared: a stated `orexis:touches` would be a second statement of what the
construct settles, and `planner.py` carries the scar of a guard that disagreed with the effect
it described. Nothing here is stored either — computed per pass, parsed once per text.
"""

from __future__ import annotations

import functools
import logging
import re

import rdflib
from rdflib import RDF, URIRef
from rdflib.collection import Collection
from rdflib.paths import AlternativePath, InvPath, MulPath, NegatedPath, SequencePath
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate, traverse
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate

from orexis_agent_progression.store import PREFIXES, bindings

log = logging.getLogger("relevance")

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
_TOKEN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


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
        return n
    traverse(node, visitPost=visit)
    return ok[0]


@functools.lru_cache(maxsize=512)
def reads_of_select(text: str) -> frozenset | None:
    """The predicates a SELECT's or a CONSTRUCT's WHERE reads, or ANYTHING if unparseable."""
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001 — unreadable is a finding
        log.debug("could not parse a query for relevance: %s", exc)
        return ANYTHING
    out: set = set()
    where = alg.get("p", alg)
    return frozenset(out) if _predicates_in(where, out) else ANYTHING


@functools.lru_cache(maxsize=512)
def writes_of_construct(text: str) -> frozenset | None:
    """The predicates a CONSTRUCT's template writes, or ANYTHING if unparseable or variable."""
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001
        log.debug("could not parse a construct for relevance: %s", exc)
        return ANYTHING
    out = set()
    for _, p, _ in alg.get("template") or ():
        if not isinstance(p, URIRef):
            return ANYTHING
        out.add(p)
    return frozenset(out)


@functools.lru_cache(maxsize=64)
def edges_of_update(text: str) -> tuple:
    """Each INSERT of an update text as a (reads, writes) edge — a derivation rule, for the
    closure. An update the parser refuses yields one edge that reads and writes ANYTHING."""
    try:
        ops = translateUpdate(parseUpdate(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001
        log.debug("could not parse a rule for relevance: %s", exc)
        return ((ANYTHING, ANYTHING),)
    edges = []
    for op in ops:
        if getattr(op, "name", None) != "Modify" or not op.get("insert"):
            continue
        writes: set = set()
        for quads in _templates(op["insert"]):
            for _, p, _ in quads:
                if not isinstance(p, URIRef):
                    writes = ANYTHING
                    break
                writes.add(p)
            if writes is ANYTHING:
                break
        reads: set = set()
        readable = _predicates_in(op.get("where"), reads) if op.get("where") is not None else True
        edges.append((frozenset(reads) if readable else ANYTHING,
                      frozenset(writes) if writes is not ANYTHING else ANYTHING))
    return tuple(edges)


def _templates(insert):
    """The triple lists of an INSERT: its default-graph triples and each GRAPH block's."""
    if insert.get("triples"):
        yield insert["triples"]
    for g in insert.get("quads", {}).values() if hasattr(insert.get("quads", {}), "values") else ():
        yield g


# --- what a want reads --------------------------------------------------------------------------

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


# --- the closure --------------------------------------------------------------------------------

_ACTIONS_Q = """
SELECT ?action ?available ?construct ?retracts WHERE {
  ?action a orexis:Action .
  OPTIONAL { ?action orexis:available ?available }
  OPTIONAL { ?action sh:construct ?construct }
  OPTIONAL { ?action orexis:retracts ?retracts }
}"""

_SUBPROPERTIES_Q = """
SELECT ?narrow ?broad WHERE { ?narrow rdfs:subPropertyOf ?broad . FILTER(?narrow != ?broad) }"""


def actions_of(query) -> dict[str, tuple]:
    """Every action the store holds as `iri -> (reads, writes)`, each ANYTHING where unreadable."""
    out = {}
    for row in bindings(query(_ACTIONS_Q)):
        if not row.get("construct"):
            #  AN ACTION STATING NO EFFECT is an action an event adopts (#506) — never on a
            #  menu, never simulated — and has no place in a closure that decides what gets
            #  simulated. Reading it as ANYTHING-writes-ANYTHING collapsed every want's
            #  closure to everything, for the market's Presenting.
            continue
        #  No precondition text is a lever with nothing to widen the want by — the afforder
        #  yields it no rows, but a construct it does carry says what it would write.
        reads = reads_of_select(row["available"]) if row.get("available") else frozenset()
        writes: set | None = set()
        for text in (row["construct"], row.get("retracts")):
            if not text:
                continue
            part = writes_of_construct(text)
            if part is None:
                writes = ANYTHING
                break
            writes |= part
        out[row["action"]] = (reads, frozenset(writes) if writes is not ANYTHING else ANYTHING)
    return out


def relevant(want_reads, actions: dict[str, tuple], rules: tuple = (),
             subproperties: dict | None = None) -> frozenset | None:
    """The actions that could serve a want reading `want_reads`, closed backward through the
    preconditions of every action and the WHERE of every rule that joins in, to a fixed point.
    ANYTHING where the want's reads are, or where the closure grows to, anything."""
    if want_reads is ANYTHING:
        return ANYTHING
    reads = set(want_reads)
    chosen: set = set()
    while True:
        widened = _widen(reads, subproperties or {})
        grew = False
        for action, (p, e) in actions.items():
            if action in chosen:
                continue
            if e is ANYTHING or e & widened:
                chosen.add(action)
                if p is ANYTHING:
                    return ANYTHING
                if not p <= reads:
                    reads |= p
                    grew = True
        for p, e in rules:
            if e is ANYTHING or e & widened:
                if p is ANYTHING:
                    return ANYTHING
                if not p <= reads:
                    reads |= p
                    grew = True
        if not grew:
            return frozenset(chosen)


def _widen(reads: set, subproperties: dict) -> set:
    """`reads` plus every narrower property the entailment would fold into one of them."""
    out = set(reads)
    frontier = list(reads)
    while frontier:
        broad = frontier.pop()
        for narrow in subproperties.get(broad, ()):
            if narrow not in out:
                out.add(narrow)
                frontier.append(narrow)
    return out


def subproperties_of(query) -> dict:
    out: dict = {}
    for row in bindings(query(_SUBPROPERTIES_Q)):
        out.setdefault(URIRef(row["broad"]), set()).add(URIRef(row["narrow"]))
    return out


def rule_edges() -> tuple:
    """Every derivation rule in every loaded package, as (reads, writes) edges."""
    from assembly import loader

    edges = []
    for path in loader.rule_files():
        edges.extend(edges_of_update(path.read_text()))
    return tuple(edges)

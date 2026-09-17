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
        #  No precondition text is a lever with nothing to widen the want by — the menu
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


def scopes(actions: dict[str, tuple], rules: tuple = ()) -> tuple[frozenset, ...]:
    """The SCOPES of a vocabulary: predicates joined wherever one action or one derivation
    reads or writes both, and separate where nothing does (#565).

    How far anything an agent does can reach. A hull's compartments are the picture — flooding
    one does not flood the next — and the sovereign ruled the word: a core concept outranks a
    niche one, so a commitment's token says what it `permits` and a want sits on the binding
    axis. Not "component", which is what this repo calls a package.

    Two wants in different scopes cannot contradict, because no action of one writes a fact
    the other reads — which is what makes it safe to plan them apart, one cone each, and to
    concatenate their plans. Independence is PROVEN this way and never read off namespaces: a
    greenhouse's water and climate words look like two vocabularies until a heater dries the
    soil, and two vans in one courier vocabulary look like one until you notice nothing they do
    touches the same van.

    Computed from relevance's own tables, so it says what the shipped rules actually do rather
    than what anyone declared. An action whose reads or writes are unreadable joins everything:
    a lever that might touch any predicate cannot be proven not to.

    **A scope here is a set of PREDICATES, and that is the limit worth naming.** Two vans are
    two scopes only over VARIABLES — a subject and a predicate together — and this sees
    predicates alone, so it separates a vocabulary and never two instances of one. Measured on
    every shipped world, it separates nothing at all: 90 predicates, one scope, whether the
    derivations are counted or the actions taken alone. That is the honest state of the claim,
    and it is why one cone per scope has nothing yet to split.
    """
    edges = list(actions.values()) + list(rules)
    known = {str(p) for reads, writes in edges
             for side in (reads, writes) if side is not ANYTHING for p in side}
    parent: dict = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(terms) -> None:
        terms = list(terms)
        for other in terms[1:]:
            a, b = find(terms[0]), find(other)
            if a != b:
                parent[a] = b

    for term in known:
        find(term)
    for reads, writes in edges:
        if reads is ANYTHING or writes is ANYTHING:
            join(known)          # unreadable: it might touch anything, so it joins everything
            continue
        join(str(p) for p in set(reads) | set(writes))
    out: dict = {}
    for term in known:
        out.setdefault(find(term), set()).add(term)
    return tuple(frozenset(v) for v in sorted(out.values(), key=lambda s: (-len(s), sorted(s))))


def spans(view, parts: tuple[frozenset, ...]) -> int:
    """How many scopes a view falls across — 1 where the want may be planned as one cone,
    more where its plan would be several concatenated. ANYTHING spans everything there is."""
    if view is ANYTHING:
        return len(parts)
    names = {str(p) for p in view}
    return sum(1 for part in parts if part & names)


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


_BRIDGES_Q = """
SELECT ?bridge ?action ?construct WHERE {
  ?bridge a orexis:Bridge ; orexis:refines ?action ; sh:construct ?construct }"""


def unkeepable_bridges(query) -> list[str]:
    """Bridges that translate an action's promise into facts NO declared action writes — a
    promise nobody could keep (#532). A taker-less action with no bridge is knowledge-only
    and admitted: planned, never executed, a wire-less world's point. A bridge is a claim
    that a level beneath exists, and this holds the claim to the actions the tree declares:
    every predicate the bridge's construct writes must be one some action's effect writes,
    whether or not that action is taken here — a level nobody executes is still a level
    somebody could plan. An unreadable construct is admitted, and an action whose writes are
    unreadable vouches for nothing: unreadable is a finding for relevance, not a refusal.
    Each fault is one sentence."""
    #  An action whose effect relevance cannot read (ANYTHING) is left out rather than let
    #  stand for everything: sensing's look is one, and letting it keep every promise would
    #  disable the gate in every world that senses.
    written: set = set()
    for _, writes in actions_of(query).values():
        if writes is not ANYTHING:
            written |= set(writes)
    faults = []
    for row in bindings(query(_BRIDGES_Q)):
        writes = writes_of_construct(row["construct"])
        if writes is None or writes is ANYTHING:
            continue
        missing = sorted(str(p).rsplit("#", 1)[-1] for p in writes if p not in written)
        if missing:
            faults.append(f"{row['bridge'].rsplit('#', 1)[-1]} refines "
                          f"{row['action'].rsplit('#', 1)[-1]} into facts no action writes "
                          f"({', '.join(missing)}) — a promise nobody could keep")
    return faults

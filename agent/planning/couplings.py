"""What a holder's CONSTRAINTS can make collide — which instances' plans may interfere under one,
read off the constraint's footprint over what the actions can reach from the present
(knowledge/domain/planning/constraint.md, one-mind-couples-the-wants-a-constraint-can-make-collide).

A constraint is a `planning:Constraint` the holder holds — what the world says is POSSIBLE, stated
in a desire's words, a shape under `planning:metWhen` or an avoided state under `planning:unmetWhen`,
and compiled by `violation.select_of` into the one select whose rows are its violations. Its
footprint is what a scope's is, one level up — the predicates it reads and the key it joins them on
— and the derivation couples two instances into one want where the constraint can join an atom some
plan for the one may write to an atom some plan for the other may write: the two-vans constraint
reads `courier:at` on vans and joins on the cell, so two parcels whose vans can meet on a cell are
one cluster, and two whose vans never can are two. A desire couples nothing, however it is
authored: an aversion is a state the agent may enter and must leave, not one no plan may make.

**READ OVER THE REACH, NOT OVER THE PUBLIC GRAPHS.** `footprint.atoms_of` reads a scope's atoms
off the public graphs alone, every pattern optional, which is right for a partition that must stand
while the agent runs. It is grid-blind: asked that way the aversion joins `van_a` to `van_b` with the
cell unbound, on a shared grid and on two grids a continent apart alike, because which cells a van
can stand on is the drive's precondition's FILTER over coordinates, and the public half of a text is
its patterns. Measured on the shipped dispatcher and on a variant with the vans on disjoint grids:
the same four rows. So the constraint is asked over the REACH — every fact some sequence of the
actions could make true from the present ground with nothing taken away, the delete-free fixpoint
of the effects' constructs over their preconditions, which is the planning literature's relaxed
reachability — and its rows are then the collisions the plans could actually make: 32 on the shared
grid, none on disjoint grids, at twelve milliseconds and seven rounds for the courier's 4x4.

**AND AN INSTANCE REACHES AN ATOM THROUGH A FILLING THAT BINDS BOTH.** Which plans may write `at`
on `van_a` is which wants `van_a` can serve, and a van serves a parcel where some filling admitted in
the reach binds the two together — the pick of that parcel into that van — exactly as a scope's key
is what the world binds a subject by. Two instances are COUPLED where one component of the terms the
constraint's rows join meets what each is bound with. Over-approximation is the safe side
throughout, as it is for a footprint: a row's every bound IRI is joined, a filling's every bound IRI
counts, and a constraint whose select cannot be run couples everything, since what cannot be read
cannot be proven not to collide.

PER PASS, IN THE DERIVATION, because the reach begins at the present: where the vans stand decides
which grid each is on, and a scope is computed at boot from what the world alone binds. A holder
that holds no constraint pays one query; the dispatcher pays the reach, measured in the runbook.

A READ, and a function over the store: it writes a working graph for the reach and takes it away
before it answers, so nothing it does outlives the call and no catalogue row is written for it.

THE HOLDER CHOOSES THE CONSTRAINTS AND NOTHING ELSE. A precondition asks for the agent as the self
(`?me a orexis:Self`), which crossed into the imaginarium the reach is read in; in an agent's store
the one holder is the self. A store holding several holders and no self — a test's world — reads
every precondition that names the agent as admitting nothing in the reach, which couples less.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import ACTION, GRAPH_PREFIX
from agent.store import NAMESPACES, Unbound, bind, graphs_of, rdflib_view, rows

from . import violation
from .ontology import CONSTRAINT_GRAPH, SHAPES
from .world_at import world_at

log = logging.getLogger("couplings")

#  WHERE THE REACH IS WRITTEN while it is computed: a working graph of the store it is asked of,
#  removed before the answer is given. Spelled by its writer, as every graph name is, and read by
#  no catalogue, since nothing reads it but this module and nothing of it outlives the call.
REACH_GRAPH = GRAPH_PREFIX + "reach"

#  A ROUND OF THE REACH is every construct asked once over what stands; the reach is monotone and
#  finite over the terms a store holds, so it closes on its own — a construct minting a fresh node
#  per row would not, and no shipped effect does, so the ceiling is a guard and never reached.
ROUNDS = 64

#  THE HOLDER'S CONSTRAINTS: every `planning:Constraint` it holds, read where a world states them;
#  the select each compiles to is read off the shapes crossed, under either polarity.
_CONSTRAINTS_Q = """SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } ORDER BY ?c"""

#  THE ACTIONS' PRECONDITIONS AND THE CONSTRUCTS OF THEIR EFFECTS — what the reach is closed over.
#  A rule's `planning:update` is a delete, and the reach deletes nothing.
_ACTIONS_Q = """
SELECT ?action ?precondition ?construct WHERE {
  ?action a orexis:Action ; planning:precondition ?precondition ;
          planning:effect/sh:rule ?r . ?r sh:construct ?construct }
ORDER BY ?action ?construct"""

_PROLOGUE = re.compile(r"^\s*(?:PREFIX\s+\S+\s+<[^>]*>\s*)+", re.I)
_CONSTRUCT = re.compile(r"^\s*CONSTRUCT\s*\{(.*)\}\s*WHERE\s*\{(.*)\}\s*$", re.S | re.I)
_HEAD = re.compile(r"^(\s*)SELECT\s+(?:DISTINCT\s+|REDUCED\s+)?(.*?)\s+WHERE\b", re.S | re.I)
_TOKEN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\b")


class Couplings:
    """What one holder's constraints can make collide: `parts`, the components of the terms the
    constraints' rows join over the reach — the vans that can meet, and the cells they meet on — and
    `bound`, each term to every term some filling admitted in the reach binds it with. Two instances
    are joined where one part meets what each is, or is bound with. `anything` where a constraint
    could not be read, and then everything is joined: the safe side."""

    def __init__(self, parts: list[frozenset[str]], bound: dict[str, frozenset[str]], *, anything: bool = False):
        self.parts = parts
        self.bound = bound
        self.anything = anything

    def joins(self, a: str, b: str) -> bool:
        """Can some constraint make a plan for `a` and a plan for `b` collide?"""
        if self.anything:
            return True
        reach_a = self.bound.get(a, frozenset()) | {a}
        reach_b = self.bound.get(b, frozenset()) | {b}
        return any(part & reach_a and part & reach_b for part in self.parts)


def couplings(store: ox.Store, holder: str, present: str, now: datetime, *, memo=None) -> Couplings | None:
    """What `holder`'s constraints can make collide, read over the reach from the `present` ground
    of `store` — or None where the holder holds no constraint, which costs one query and couples
    nothing. `now` is the pass's instant; `memo` the pass's, for the graph lists `world_at` keeps."""
    constraints = rows(store, _CONSTRAINTS_Q, graphs_of(store, CONSTRAINT_GRAPH), holder=holder)
    if not constraints:
        return None
    #  WHAT EACH COMPILES TO, off the shapes a constraint's test lives among — its own graph's, or
    #  a domain's. One that will not compile couples everything, as one that will not run does:
    #  what cannot be read cannot be proven not to collide.
    shapes = rdflib_view(store, *graphs_of(store, CONSTRAINT_GRAPH, SHAPES))
    selects = []
    for c in constraints:
        try:
            text = violation.select_of(shapes, c["c"])
        except violation.Unsupported as exc:
            log.warning("a constraint cannot be compiled; every instance is coupled: %s", exc)
            return Couplings([], {}, anything=True)
        if text is not None:
            selects.append(text)
    graphs = world_at(store, present, now=now, memo=memo)
    actions = rows(store, _ACTIONS_Q, graphs_of(store, ACTION, at=now))
    default = [ox.NamedNode(g) for g in graphs] + [ox.NamedNode(REACH_GRAPH)]
    try:
        texts = [_composed(a["construct"], bind(a["precondition"])) for a in actions]
    except (ValueError, Unbound) as exc:
        log.warning("a construct could not be closed over its precondition; every instance is coupled: %s", exc)
        return Couplings([], {}, anything=True)
    try:
        try:
            _reach(store, texts, default)
        except Exception as exc:                            # noqa: BLE001 — unreadable is a finding
            #  A COMPOSED TEXT THE ENGINE REFUSES is the same finding as one that would not compose:
            #  a construct whose own WHERE rebinds a parameter the precondition projects —
            #  `BIND($tank AS ?tank)`, the shape every planning case writes — parses alone and not
            #  joined, and a pass that died here over it found nothing (#902, measured).
            log.warning("a construct could not be run over the reach; every instance is coupled: %s", exc)
            return Couplings([], {}, anything=True)
        parts = _parts(store, selects, default)
        if parts is None:
            return Couplings([], {}, anything=True)
        bound = _bound(store, [a["precondition"] for a in actions], default)
    finally:
        store.remove_graph(ox.NamedNode(REACH_GRAPH))
    return Couplings(parts, bound)


def _composed(construct: str, precondition: str) -> str:
    """The construct closed over its precondition as ONE text: the template over a group holding
    the precondition as a subselect and the construct's own WHERE after it, so what the
    precondition binds — the action's parameters, projected — is what the template is filled with,
    and the construct's own patterns, hanoi's `OPTIONAL` and `BIND`, read them in the same group.
    The prologues of both go at the head; a `$token` of the template is the variable the
    precondition projects under that name. Refuses a construct that is not of the one shape."""
    p1, body = _split(construct)
    p2, select = _split(precondition)
    m = _CONSTRUCT.match(body)
    if m is None:
        raise ValueError(f"not a CONSTRUCT … WHERE: {body[:60]!r}")
    template = _TOKEN.sub(lambda mm: "?" + mm.group(1), m.group(1))
    own = _TOKEN.sub(lambda mm: "?" + mm.group(1), m.group(2))
    return f"{p1}\n{p2}\nCONSTRUCT {{ {template} }} WHERE {{ {{ {select} }} {own} }}"


def _split(text: str) -> tuple[str, str]:
    m = _PROLOGUE.match(text)
    return (m.group(0), text[m.end():]) if m else ("", text)


def _reach(store: ox.Store, texts: list[str], default: list) -> int:
    """Close the reach: every construct over what stands, round after round, until no round adds a
    quad. Delete-free, so it only grows, and finite over the store's terms. The rounds taken."""
    scratch = default[-1]
    rounds, held = 0, -1
    while rounds < ROUNDS:
        rounds += 1
        for text in texts:
            for t in store.query(text, prefixes=NAMESPACES, default_graph=default):
                store.add(ox.Quad(t.subject, t.predicate, t.object, scratch))
        size = sum(1 for _ in store.quads_for_pattern(None, None, None, scratch))
        if size == held:
            break
        held = size
    return rounds


def _parts(store: ox.Store, selects: list[str], default: list) -> list[frozenset[str]] | None:
    """The components of what the constraints' rows join over the reach: every IRI one row binds is
    joined to every other, across every row of every constraint. The select is asked with every
    variable projected, since the join key may be one the head left out — `?other`, in the
    dispatcher's — and with its original head where that will not run. None where a select will not
    run either way, which is a constraint nobody can read."""
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for text in selects:
        text = re.sub(r"\$this\b", "?this", bind(text))
        solutions = None
        for attempt in (_HEAD.sub(r"\1SELECT * WHERE", text, count=1), text):
            try:
                found = store.query(attempt, prefixes=NAMESPACES, default_graph=default)
                names = [v.value for v in found.variables]
                solutions = list(found)
                break
            except Exception as exc:                        # noqa: BLE001 — unreadable is a finding
                log.debug("a constraint's select would not run over the reach: %s", exc)
        if solutions is None:
            return None
        for solution in solutions:
            terms = [str(solution[n].value) for n in names
                     if solution[n] is not None and isinstance(solution[n], ox.NamedNode)]
            for other in terms[1:]:
                a, b = find(terms[0]), find(other)
                if a != b:
                    parent[a] = b
    out: dict = {}
    for term in list(parent):
        out.setdefault(find(term), set()).add(term)
    return [frozenset(v) for v in sorted(out.values(), key=lambda s: sorted(s))]


def _bound(store: ox.Store, preconditions: list[str], default: list) -> dict[str, frozenset[str]]:
    """Each term to every term some filling admitted in the reach binds it with — the parcel to the
    vans that can pick it and the cells it can be dropped on. A precondition is asked as `admit`
    asks it, over the reach in the present's place; one that will not run binds nothing, which is
    the under-approximation, so a text that fails here is said."""
    out: dict[str, set[str]] = {}
    for text in preconditions:
        try:
            found = store.query(bind(text), prefixes=NAMESPACES, default_graph=default)
            names = [v.value for v in found.variables]
            for solution in found:
                terms = {str(solution[n].value) for n in names
                         if solution[n] is not None and isinstance(solution[n], ox.NamedNode)}
                for term in terms:
                    out.setdefault(term, set()).update(terms - {term})
        except Exception as exc:                            # noqa: BLE001 — said, since it under-approximates
            log.warning("a precondition would not run over the reach, and binds nothing there: %s", exc)
    return {k: frozenset(v) for k, v in out.items()}

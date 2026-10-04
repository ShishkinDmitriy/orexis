"""`scope_actions`: the actions the store holds, clustered into the scopes their effects join,
written back to the store — the function that makes the scope partition data (scope-actions),
and a FUNCTION OVER THE STORE: handed the engine, a `pyoxigraph.Store`, and nothing else.
After the call, the store says which predicates some one action or derivation reads or writes
together, and which scope each predicate and each action is in; `derive_wants` clusters a
desire's results by it and reads no action.

The partition is computed from what the shipped rules actually do — never read off namespaces
— over the edges `footprint` reads off an action, which a narrowing closure would read too, and
the edges each loaded derivation makes, which genesis put in the store beside the actions
(`describe_derivations`). It is a function of the actions and the rules loaded, neither of
which changes while the agent runs, so this runs at boot, once, and whenever they are rebuilt;
it used to run inside every derivation.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent import clock
from agent.ontology import OREXIS
from agent.store import NAMESPACES, graphs_of, rows

from . import footprint
from .ontology import DERIVATION_GRAPH
from .footprint import ANYTHING
from .find_scopes import STANDING_Q

log = logging.getLogger("scope_actions")


def scope_actions(store: ox.Store) -> None:
    """Cluster every action the store holds into scopes and write them, replacing what stood.

    An action is in the scope its reads and writes lie in — one by construction, since an
    action touching two would have joined them. An action stating no effect is in no scope, as
    no world admits it; one whose effect cannot be read joins everything and is in the one scope
    that holds everything. A scope is named for the graph it is written in and its place in the
    partition, largest first (`scopes.py` names both), so the same actions write the same text.

    A FUNCTION OVER THE ENGINE, and it names no agent: the actions come from the public graphs
    the catalogue describes, the derivations' edges from the graph genesis wrote them into, and
    the partition that comes out is the STORE's — every agent reading one store would compute
    the same one from the same rows, so there is nobody to name it after (`scopes.py`).
    """
    now = clock.now()
    atoms = footprint.atoms_of(store, now)
    edges = footprint.stored_edges(store, graphs_of(store, DERIVATION_GRAPH))
    parts = _partition(atoms, edges)
    #  WHAT EACH SCOPE HOLDS: the predicates and the terms of its atoms, and the actions a filling
    #  of which is in it. A predicate or a term that falls in two scopes is in neither for a
    #  reader — a reader asking it is told nothing, which joins every group, the safe side — where
    #  an action in two scopes is admitted in both.
    part_of = {atom: n for n, part in enumerate(parts, 1) for atom in part}
    where: dict = {}
    for n, part in enumerate(parts, 1):
        for predicate, _ in part:
            where.setdefault(("p", predicate), set()).add(n)
    #  A FILLING'S TERMS BELONG TO THE SCOPE ITS ATOMS FALL IN — one, since a filling's atoms are
    #  joined — so the valve a filling is of is the member a search tells its candidates by.
    for fillings in atoms.values():
        for atoms_, terms in (fillings if fillings is not ANYTHING else ()):
            scopes_of = {part_of[a] for a in atoms_ if a in part_of}
            for term in terms:
                where.setdefault(("t", term), set()).update(scopes_of or set(range(1, len(parts) + 1)))
    written = []
    for n, part in enumerate(parts, 1):
        scope = _scope_name(n)
        members = {m for (kind, m), scopes in where.items() if scopes == {n}}
        actions = {action for action, fillings in atoms.items()
                   if fillings is ANYTHING or any(atom in part for atoms_, _ in fillings for atom in atoms_)}
        written.append((scope, members, actions))
    _save_scopes(store, written)
    log.info("%d action(s) in %d scope(s)", len(atoms), len(parts))


#  THE STORE'S SCOPES, and the name is this module's because this module replaces the graph
#  whole on every run. Nobody's and taking no id: the partition is a function of the actions
#  the store holds and the derivations loaded, which are the same rows for everyone reading
#  one store, so there is nobody to name it after. Spelled in `ontology.ttl` too, beside the
#  class, because the vocabulary declares this instance publicly as it declares the world's
#  and the actions'; a READER asks the class and never this.
SCOPES_GRAPH = "http://example.org/orexis/graph/scopes"

SCOPES_Q = """
SELECT ?member ?scope WHERE { ?member planning:inScope ?scope }"""

#  EVERY STANDING SCOPE GRAPH, asked of the catalogue by class — what a run replaces, whatever
#  each is called, including a per-agent one a volume was left with before the partition
#  became the store's.
STANDING_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } }
ORDER BY ?g"""


def _scope_name(n: int) -> str:
    """The name of the nth scope in the partition, largest first — the graph's own, suffixed,
    so the same actions write the same text. This module names both the graph and what is in
    it; `scope_actions` decides the partition and asks for the names."""
    return f"{SCOPES_GRAPH}/{n}"


def _save_scopes(store: ox.Store, scopes: list[tuple[str, set[str], set[str]]]) -> None:
    """Replace the store's scopes with these — `(scope, members, actions)` each, the members the
    predicates and the terms in no other scope — and say what the graph is. Written whole, and classified even when empty: a store with no scope
    graph has never been scoped, which `derive_wants` refuses to guess about.

    ONE UPDATE OVER THE ENGINE: every standing scope graph asked of the catalogue by class and
    dropped, then the graph and its catalogue row together, the catalogue found by its own row
    and every kind the vocabulary puts a scope graph beneath written from one
    `rdfs:subClassOf` step — the closure is materialised at genesis, so one step is every step.
    """
    standing = [row["g"] for row in rows(store, STANDING_Q)]
    graph = SCOPES_GRAPH
    blocks = []
    for scope, held, actions in scopes:
        members = " ".join(f"<{m}> planning:inScope <{scope}> ." for m in sorted(held | actions))
        blocks.append(f"  <{scope}> a planning:Scope .\n  {members}")
    dropped = "".join(
        f"DROP SILENT GRAPH <{g}> ;\n"
        f"DELETE {{ GRAPH ?cat {{ <{g}> ?p ?o }} }} WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{g}> ?p ?o }} }} ;\n"
        for g in standing)
    store.update(dropped + f"""
INSERT {{
  GRAPH <{graph}> {{
{chr(10).join(blocks)}
  }}
  GRAPH ?cat {{ <{graph}> a planning:ScopeGraph ; orexis:arrivedBy <{OREXIS + "Derived"}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ planning:ScopeGraph rdfs:subClassOf ?kind }} }}""",
                 prefixes=NAMESPACES)




def _partition(atoms: dict[str, list | None], rules: tuple = ()) -> tuple[frozenset, ...]:
    """The SCOPES of a vocabulary: atoms — a predicate on a key — joined wherever one filling of one
    action reads or writes both, and separate where nothing does (#565, #593).

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

    **A SCOPE IS OVER KEYS, NOT PREDICATES ALONE.** Over predicates it separated a vocabulary and
    never two instances of one: a pump and a heater both write a reading's side, and were one
    scope though the pump's reading is the soil's and the heater's the air's. An atom is a
    predicate on a KEY — the subject's own value, or the public values the filling binds it by, a
    reading's feature and property — read per filling off the public graphs (`footprint.atoms_of`);
    two fillings join only where they share an atom, and an atom keyed by nothing is every atom of
    its predicate, which is the predicate partition again. An action whose texts cannot be read
    joins everything. A derivation's edges are predicates and join every key of theirs.
    """
    edges = [atoms_ for fillings in atoms.values() if fillings is not ANYTHING for atoms_, _ in fillings]
    known: set = set()
    for atoms_ in edges:
        known |= atoms_
    for reads, writes in rules:
        for side in (reads, writes):
            if side is not ANYTHING:
                known |= {(str(p), None) for p in side}
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(items) -> None:
        items = list(items)
        for other in items[1:]:
            a, b = find(items[0]), find(other)
            if a != b:
                parent[a] = b

    for atom in known:
        find(atom)
    if any(fillings is ANYTHING for fillings in atoms.values()):
        join(known)                  # unreadable: it might touch anything, so it joins everything
    for atoms_ in edges:
        join(atoms_)
    for reads, writes in rules:
        if reads is ANYTHING or writes is ANYTHING:
            join(known)
            continue
        join((str(p), None) for p in set(reads) | set(writes))
    #  AN ATOM KEYED BY NOTHING IS EVERY ATOM OF ITS PREDICATE: a subject the world alone binds
    #  nothing of may be any instance, so its predicate's atoms are one.
    by_predicate: dict = {}
    for predicate, key in known:
        by_predicate.setdefault(predicate, []).append((predicate, key))
    for predicate, members in by_predicate.items():
        if any(key is None for _, key in members):
            join(members)
    out: dict = {}
    for atom in known:
        out.setdefault(find(atom), set()).add(atom)
    return tuple(frozenset(v) for v in sorted(out.values(), key=lambda s: (-len(s), sorted(map(str, s)))))

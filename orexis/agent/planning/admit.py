"""What one world ADMITS — a candidate per action per legal filling — written as the edges
that leave it.

**ONE PER ACTION PER LEGAL FILLING**, and the filling is the point: an action's
`orexis:available` is a SELECT projecting the parameters the action declares it takes, so its
ROWS are the candidates. It is not a filter the search applies to a list it already had — it is
where the list comes from, and where `$tank = tank1` comes from.

**WRITTEN, NOT RETURNED.** A candidate was a Python value in flight — a frozen class of an
action and a binding — carried from here to the fork and written only if taken. Every candidate
of an opened world IS taken, forked or passed over, so writing them as they are found writes
the same rows a little earlier and hands nothing across: `expand` reads back what leaves the
world and has not been weighed for its want, `take` reads what a candidate fills off its row,
and the class is gone. A candidate is named for the world it would reach, `<child>.by`, so
the edge and the world it makes are one spelling apart, for eyes.

**THE WORLD IS ASKED ABOUT, NOT HELD**: `world_at` says what a precondition reads there, and
the precondition names no graph to get it (#666). **AND EVERY ACTION IS ASKED.** There was
an `only` parameter — the set worth asking at all, which the relevance closure computes from
what a want READS — and no caller passed it; narrowing returns with the closure.

`me` is the one identifier a process is handed, and the one token a precondition may read.
"""

from __future__ import annotations

from urllib.parse import quote

from orexis.agent.ontology import GRAPH_PREFIX, PUBLIC, local_of
from orexis.agent.store import Raw, bind, bindings, graphs_of, query, remember, render, update

from .world_at import world_at

#  Where a possible world's readings sit. Under the same root as every other graph, because a
#  graph IRI is a graph IRI — but in a store nothing else can open, which is what keeps
#  `planning:PossibleGraph`'s promise that nothing here survives anything.
POSSIBLE = GRAPH_PREFIX + "possible/"

#  WHAT THE VOCABULARY DECLARES, and the only reason to ask: an action carries the SELECT that
#  says when it is possible, and running it is the only way to learn what a world affords.
#  `STR(?takes)` because GROUP_CONCAT over an IRI binds NOTHING in this engine — no column at
#  all, measured. An action declaring no parameter yields the empty string, which is a legal
#  answer: it is filled with nothing and affords at most one row.
_ACTIONS_Q = """SELECT ?action ?available (GROUP_CONCAT(DISTINCT STR(?takes); separator=" ") AS ?takes_) WHERE {
  ?action a orexis:Action ; orexis:available ?available .
  OPTIONAL { ?action orexis:takes ?takes }
} GROUP BY ?action ?available"""

_ADMIT_U = """
INSERT { GRAPH ?cat { $edges } } WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"""


def admit(store, world: str, me: str, *, memo=None) -> None:
    """Write every candidate `world` admits for the agent `me`: one per action per row its
    precondition binds there, each saying which world it leaves (`planning:from`), which
    action it fills and, one triple per parameter under the parameter's own IRI, what it is
    filled with. Idempotent: a world admitted twice says the same rows.

    THE ROW IS WHAT THE PRECONDITION BOUND, held to what the action says it TAKES: a projected
    variable the action does not declare is ignored, and a declared parameter the row left
    unbound is absent — an action with an OPTIONAL hop affords rows of two shapes, and both
    are honest. ZERO IS ORDINARY: nine of the eleven actions a simulation agent loads are
    admitted by nothing. MANY is ordinary too — a supplier with three valves admits `Serving`
    three times, and choosing between them is the whole of what the search does there.
    """
    graphs = world_at(store, world, memo=memo)
    edges = []
    for action in remember(memo, ("actions",), lambda: sorted(
            bindings(query(store, _ACTIONS_Q, graphs_of(store, PUBLIC))), key=lambda r: r["action"])):
        #  A precondition carrying a token nobody binds REFUSES rather than reaching the engine
        #  as a free variable (#500), so what is offered is what a premise may read: `$me`.
        params = {local_of(p): p for p in (action.get("takes_") or "").split()}
        for row in bindings(query(store, bind(action["available"], me=me), graphs)):
            filling = sorted((iri, row[local]) for local, iri in params.items() if row.get(local))
            segment = "-".join(quote(local_of(part), safe="")
                               for part in (action["action"], *(v for _, v in filling)))
            child = f"{world}.{segment}" if world.startswith(POSSIBLE) else POSSIBLE + segment
            cand = child + ".by"
            edges.append(f"<{cand}> a planning:Candidate ; planning:from <{world}> ; "
                         f"planning:fills <{action['action']}> .\n"
                         + "".join(f"<{cand}> <{p}> {_term(v)} .\n" for p, v in filling))
    if edges:
        update(store, bind(_ADMIT_U, edges=Raw("".join(edges))))


def _term(value: str) -> str:
    """One binding's value as the text of the term it is — an IRI where it looks like one,
    else a literal."""
    import pyoxigraph as ox
    return render(value) if "://" in value else render(ox.Literal(value))

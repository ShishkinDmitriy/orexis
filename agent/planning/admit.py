"""What one world ADMITS — a candidate per action per legal filling — written as the edges
that leave it.

**ONE PER ACTION PER LEGAL FILLING**, and the filling is the point: an action's
`planning:precondition` is a SELECT projecting the parameters the action declares it takes, so its
ROWS are the candidates. It is not a filter the search applies to a list it already had — it is
where the list comes from, and where `$tank = tank1` comes from.

**WRITTEN, NOT RETURNED.** A candidate was a Python value in flight — a frozen class of an
action and a binding — carried from here to the fork and written only if taken. Every candidate
of an opened world IS taken, forked or passed over, so writing them as they are found writes
the same rows a little earlier and hands nothing across: `expand` reads back what leaves the
world and has not been weighed for its want, `take` reads what a candidate fills off its row,
and the class is gone.

**A CANDIDATE IS NAMED BY A MINT NUMBER, AND THE PATH IS ROWS** (#486). The counter is the
store's — the highest `planning:minted` any candidate or world carries, read once per pass and
advanced per candidate written — so the name is opaque, short and never repeated in one store,
and the number rides on the row as `planning:minted`: the order the pass admitted candidates,
which is the order they are taken in and the frontier's tie-break. The world a candidate makes
takes the same number, so the edge and the world at its end are one spelling apart, for eyes
(`possible/17.by` makes `possible/17`), and `take` reads the number off the row rather than
the name. It was a path — `<parent>.<action>-<values>`, URL-quoted — and an identifier
carrying structure collided once (two fillings differing only in a value nobody had put in
the segment), needed escaping, grew with depth, and was read back by nothing: `planning:by`,
`planning:from` and `planning:fills` already say what reached a world.

**THE WORLD IS ASKED ABOUT, NOT HELD**: `world_at` says what a precondition reads there, and
the precondition names no graph to get it (#666). **AND EVERY ACTION OF THE SCOPE IS ASKED**,
`only` naming them, and every filling of the scope, `elsewhere` naming the terms that are another's:
an action of another scope writes nothing a want of this one reads, so its
steps fork worlds the met-test cannot tell apart — a courier's drive, taken in hanoi's search
once a world combined the two domains, spent the budget and moved no disk. None asks every
action, which a store of one scope is.

A precondition reads NO token: it asks for the agent as `?me a orexis:Self`, the self the boot
wrote and the imaginarium copied in with the beliefs, so nobody hands it who is asking.
"""

from __future__ import annotations

from agent.ontology import ACTION, GRAPH_PREFIX, local_of
from agent.store import Raw, bind, bindings, catalogue_of, graphs_of, query, remember, render, rows, update

from .next_ground import next_ground
from .ontology import WAIT
from .world_at import world_at

#  WHETHER THE STORE HOLDS THE WAIT, among the actions: every agent's does, since the planning package
#  ships it, and a case standing a store in from its own documents holds it only where it says so.
WAIT_Q = """SELECT ?w WHERE { $wait a orexis:Action BIND($wait AS ?w) } LIMIT 1"""

#  Where a possible world's readings sit. Under the same root as every other graph, because a
#  graph IRI is a graph IRI — but in a store nothing else can open, which is what keeps
#  `planning:PossibleGraph`'s promise that nothing here survives anything.
POSSIBLE = GRAPH_PREFIX + "possible/"

#  WHAT THE VOCABULARY DECLARES, and the only reason to ask: an action carries the SELECT that
#  says when it is possible, and running it is the only way to learn what a world affords.
#  `STR(?takes)` because GROUP_CONCAT over an IRI binds NOTHING in this engine — no column at
#  all, measured. An action declaring no parameter yields the empty string, which is a legal
#  answer: it is filled with nothing and affords at most one row.
_ACTIONS_Q = """SELECT ?action ?precondition (GROUP_CONCAT(DISTINCT STR(?takes); separator=" ") AS ?takes_) WHERE {
  ?action a orexis:Action ; planning:precondition ?precondition .
  OPTIONAL { ?action orexis:takes ?takes }
} GROUP BY ?action ?precondition"""

_ADMIT_U = """
INSERT { GRAPH ?cat { $edges } } WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"""

#  WHAT THE WORLD ALREADY ADMITS: each candidate leaving it, the action it fills and every
#  parameter it is filled with — so a world admitted again, or a re-rooted world whose
#  candidates were handed to it by `reroot`, gains only the candidates it did not have.
_ADMITTED_Q = """
SELECT ?c ?action ?p ?v WHERE {
  GRAPH $cat { ?c a planning:Candidate ; planning:from $world ; planning:fills ?action .
               OPTIONAL { ?c ?p ?v . FILTER(?p NOT IN (planning:from, planning:fills, planning:minted, rdf:type)) } } }"""

#  THE HIGHEST MINT NUMBER IN THE STORE, candidate or world — the names are the store's, so the
#  counter is too: a second pass over one store, and a cone `reroot` kept, mint above it.
_MINTED_Q = """
SELECT (MAX(?m) AS ?n) WHERE { GRAPH $cat { ?w planning:minted ?m } }"""


def admit(store, world: str, *, only=None, elsewhere=frozenset(), memo=None) -> None:
    """Write every candidate `world` admits for the self: one per action per row its
    precondition binds there, each saying which world it leaves (`planning:from`), which
    action it fills, where it came in the order of minting (`planning:minted`, which names it)
    and, one triple per parameter under the parameter's own IRI, what it is filled with.
    Idempotent by FILLING and not by name: a world admitted twice says the same rows, and a
    world that already admits a candidate for an action with a filling — under whatever name,
    since a candidate handed to a re-rooted ground by `reroot` was minted in an earlier pass —
    is not given a second one for it, and the counter does not move for it.

    THE FILLINGS ARE NUMBERED IN A FIXED ORDER — by action, then by what they are filled with —
    so two traces of one search compare: the engine's row order is not promised, and a number
    handed out in it would make the taking order, and every tie-break after it, a different
    one per run.

    THE ROW IS WHAT THE PRECONDITION BOUND, held to what the action says it TAKES: a projected
    variable the action does not declare is ignored, and a declared parameter the row left
    unbound is absent — an action with an OPTIONAL hop affords rows of two shapes, and both
    are honest. ZERO IS ORDINARY: nine of the eleven actions a simulation agent loads are
    admitted by nothing. MANY is ordinary too — a supplier with three valves admits `Serving`
    three times, and choosing between them is the whole of what the search does there.

    AND A SCOPE ADMITS A FILLING, NOT AN ACTION (#593): one action filled two ways — a heater on the
    air and a lamp on the light — is in two scopes, and the air's search is not the lamp's. A filling
    one of whose values is a member of another scope, `elsewhere`, is that scope's and is not written
    here; a value no scope holds alone — the agent, the bed — tells nothing and refuses nothing.
    """
    graphs = world_at(store, world, memo=memo)
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    admitted: dict[tuple, set] = {}
    for r in rows(store, _ADMITTED_Q, (), world=world, cat=cat):
        held = admitted.setdefault((r["c"], r["action"]), set())
        if r.get("p"):
            held.add((r["p"], r["v"]))
    already = {(action, frozenset(filling)) for (_, action), filling in admitted.items()}
    fillings = []
    for action in remember(memo, ("actions",), lambda: sorted(
            bindings(query(store, _ACTIONS_Q, graphs_of(store, ACTION))), key=lambda r: r["action"])):
        if only is not None and action["action"] not in only:
            continue
        #  A precondition carrying a token nobody binds REFUSES rather than reaching the engine
        #  as a free variable (#500), and a precondition is offered none: it asks the self for the agent.
        params = {local_of(p): p for p in (action.get("takes_") or "").split()}
        for row in bindings(query(store, bind(action["precondition"]), graphs)):
            filling = sorted((iri, row[local]) for local, iri in params.items() if row.get(local))
            if (action["action"], frozenset(filling)) in already or any(v in elsewhere for _, v in filling):
                continue
            if (action["action"], filling) not in fillings:
                fillings.append((action["action"], filling))
    #  AND A WAIT, where a ground whose identity differs from the one this world stands in is laid after
    #  it (#920, `next_ground`): the planning package's own action, filled with nothing, in every
    #  scope, and stating no precondition, since what admits it is the timeline and no fact a world
    #  holds. Where nothing read is predicted to change there is nothing to wait for, and a wait
    #  landing where nothing read has moved would be the world it left.
    if (only is None or WAIT in only) and (WAIT, frozenset()) not in already \
            and remember(memo, ("waits",), lambda: bool(rows(store, WAIT_Q, graphs_of(store, ACTION), wait=WAIT))) \
            and next_ground(store, world, memo=memo) is not None:
        fillings.append((WAIT, []))
    if not fillings:
        return
    #  THE MINT COUNTER IS THE STORE'S: read off it once per pass, advanced per candidate written,
    #  and the memo keeps where it stands so a pass resumed reads MAX again and never below it.
    minted = remember(memo, ("minted",), lambda: int(rows(store, _MINTED_Q, (), cat=cat)[0].get("n") or 0))
    edges = []
    for action, filling in sorted(fillings):
        minted += 1
        cand = f"{POSSIBLE}{minted}.by"
        edges.append(f"<{cand}> a planning:Candidate ; planning:from <{world}> ; "
                     f"planning:fills <{action}> ; planning:minted {minted} .\n"
                     + "".join(f"<{cand}> <{p}> {_term(v)} .\n" for p, v in filling))
    if memo is not None:
        memo.put(("minted",), minted)
    update(store, bind(_ADMIT_U, edges=Raw("".join(edges))))


def _term(value: str) -> str:
    """One binding's value as the text of the term it is — an IRI where it looks like one,
    else a literal."""
    import pyoxigraph as ox
    return render(value) if "://" in value else render(ox.Literal(value))

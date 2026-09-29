"""Handing a pass's plans down — the last thing planning does, and the only thing it writes for
another layer: plans, into the belief base, in that layer's words.

A pass writes what it found into the imaginarium it searched in: one `planning:PlanGraph` per
want, holding the steps in EXECUTION's own words. That store outlives the pass and dies with the
Planner. This is the crossing — every plan found for a want nothing is already walking, PUBLISHED
into the belief base once, as an `orexis:PlanGraph` under a name of its own, its root saying which
want it `execution:pursues`, and beside it what the want was derived from, which execution tells
its landings by. Planning owns it and it stays; the executor adopts it by reference, and planning
never calls it (planning-and-execution-meet-at-the-store).

**A NAME OF ITS OWN**, and its steps' with it: the imaginarium names a plan for its want and a step
for its plan, so a second plan for one want would name its steps as the first did, and an act on
record for the first would read as the second's. Published, the plan and every step move under a
name minted for this plan.

**IT IS A COPY AND NOT A REWRITE**, which is why the search writes a step as `execution:Step` in
the first place: a translation on the way would be a second place the two shapes could disagree.
What the search added of its own — that the graph is a `planning:Plan`, which want it is for,
why the pass ended, what it was scored to spend — crosses with the rest and is simply not read
below. QUADS AND NOT TEXT: a serialise-and-reparse relabels blank nodes.

**A PLAN WITH NO STEPS DOES NOT CROSS.** It is an ANSWER — the want was already met, no lever
points at it, or none reached it inside the budget — and an answer is not a commitment.

**A PLAN FOR A WANT BEING WALKED DOES NOT CROSS EITHER**: the plan graph of a want an intention
pursues, or a plan published and not yet adopted pursues, is still in the imaginarium, since that outlives the
pass, and it is not the pass's to hand down twice. Absorbing a second plan by the agent's
patience is the executor's, when it commits.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

import uuid

from agent.ontology import GRAPH_PREFIX, OREXIS, PLAN, local_of
from agent.store import Raw, add_quads, bind, entry, forget_graph, graphs_of, quads, rows, update

from .ontology import PLAN_GRAPH, WANT

log = logging.getLogger("publish_plan")



#  WHICH WANT A PLAN IS FOR, off the plan's own root, and whether that want still stands.
_STANDS_Q = """SELECT ?w WHERE { $want a planning:Want . BIND($want AS ?w) } LIMIT 1"""
_FOR_Q = """SELECT ?want WHERE { GRAPH $plan { $plan planning:for ?want } }"""
_STEPS_Q = """SELECT ?step WHERE { GRAPH $plan { ?step a execution:Step } } LIMIT 1"""
_DERIVED_Q = """SELECT ?d WHERE { GRAPH ?g { $want prov:wasDerivedFrom ?d } }"""


def publish_plan(imaginarium: ox.Store, beliefs: ox.Store, me: str, walking: set[str]) -> list[str]:
    """Hand every plan the pass left in `imaginarium` down into `beliefs`, the agent `me`'s, for a
    want not in `walking`. The plan graphs written.

    The plans are asked for BY CLASS — `planning:PlanGraph`, whatever the pass named them —
    which is the same read every other door here makes and the reason a pass classifies what it
    writes.
    """
    handed = []
    for graph in sorted(graphs_of(imaginarium, PLAN_GRAPH)):
        found = rows(imaginarium, bind(_FOR_Q, plan=Raw(f"<{graph}>")))
        if not found:
            #  A PLAN GRAPH THAT NAMES NO WANT is one nobody can carry out on anyone's behalf.
            log.error("a plan graph names no want, so it cannot be published: %s", graph)
            continue
        want = found[0]["want"]
        if not rows(imaginarium, _STANDS_Q, graphs_of(imaginarium, WANT), want=want):
            #  A PLAN WHOSE WANT IS GONE is nobody's: the want was reached, or withdrawn from the
            #  beliefs and taken back by the refresh, and the plan graph the imaginarium kept
            #  would be walked a second time — measured on the tower, whose goal was reached in
            #  the courier's imaginarium and re-committed from the puzzle's. Dropped with it.
            forget_graph(imaginarium, graph)
            continue
        if want in walking or not rows(imaginarium, bind(_STEPS_Q, plan=Raw(f"<{graph}>"))):
            continue
        published = f"{GRAPH_PREFIX}plan/{local_of(me)}/{local_of(want)}.{uuid.uuid4().hex[:8]}"
        moved = lambda term: (ox.NamedNode(published + term.value[len(graph):])
                              if isinstance(term, ox.NamedNode) and term.value.startswith(graph) else term)
        name = ox.NamedNode(published)
        add_quads(beliefs, (ox.Quad(moved(q.subject), q.predicate, moved(q.object), name) for q in quads(imaginarium, graph)))
        derived = [f"<{want}> prov:wasDerivedFrom <{r['d']}> ." for r in rows(imaginarium, _DERIVED_Q, (), want=want)]
        update(beliefs, f"""INSERT DATA {{
  GRAPH <{published}> {{ <{published}> execution:pursues <{want}> . {' '.join(derived)} }}
  {entry(beliefs, published, PLAN, OREXIS + "Recorded", me)} }}""")
        handed.append(published)
    return handed

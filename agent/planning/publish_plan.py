"""Handing a pass's plans down — the last thing planning does, and the only thing it writes for
another layer: plans, into the belief base, in that layer's words.

A pass writes what it found into the imaginarium it searched in: one `planning:PlanGraph` per
want, holding the steps in EXECUTION's own words. That store outlives the pass and dies with the
Planner. This is the crossing — every plan found for a want nothing is already walking, copied
into the belief base as an `execution:PlanGraph`, its root saying which want it
`execution:pursues`, and beside it what the want was derived from, which execution tells its
landings by. The executor takes it up, commits it and forgets the graph: planning never calls it
(a-package-starts-itself).

**IT IS A COPY AND NOT A REWRITE**, which is why the search writes a step as `execution:Step` in
the first place: a translation on the way would be a second place the two shapes could disagree.
What the search added of its own — that the graph is a `planning:Plan`, which want it is for,
why the pass ended, what it was scored to spend — crosses with the rest and is simply not read
below. QUADS AND NOT TEXT: a serialise-and-reparse relabels blank nodes.

**A PLAN WITH NO STEPS DOES NOT CROSS.** It is an ANSWER — the want was already met, no lever
points at it, or none reached it inside the budget — and an answer is not a commitment.

**A PLAN FOR A WANT BEING WALKED DOES NOT CROSS EITHER**: the plan graph of a want an intention
pursues, or a plan handed down pursues, is still in the imaginarium, since that outlives the
pass, and it is not the pass's to hand down twice. Absorbing a second plan by the agent's
patience is the executor's, when it commits.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.ontology import OREXIS
from agent.store import Raw, add_quads, bind, entry, forget_graph, graphs_of, quads, rows, update

from .ontology import PLAN_GRAPH, WANT

log = logging.getLogger("publish_plan")

#  WHAT A PLAN IS HANDED DOWN AS: execution's kind, which the executor takes up.
HANDED = "http://example.org/orexis/execution#PlanGraph"

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
            log.error("a plan graph names no want, so it cannot be handed down: %s", graph)
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
        name = ox.NamedNode(graph)
        forget_graph(beliefs, graph)
        add_quads(beliefs, (ox.Quad(q.subject, q.predicate, q.object, name) for q in quads(imaginarium, graph)))
        derived = [f"<{want}> prov:wasDerivedFrom <{r['d']}> ." for r in rows(imaginarium, _DERIVED_Q, (), want=want)]
        update(beliefs, f"""INSERT DATA {{
  GRAPH <{graph}> {{ <{graph}> execution:pursues <{want}> . {' '.join(derived)} }}
  {entry(beliefs, graph, HANDED, OREXIS + "Recorded", me)} }}""")
        handed.append(graph)
    return handed

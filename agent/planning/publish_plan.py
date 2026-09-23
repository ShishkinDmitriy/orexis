"""Handing a pass's plans down — the last thing planning does, and the only thing it does to
another layer's store.

A pass writes what it found into the imaginarium it searched in: one `planning:PlanGraph` per
want, holding the steps in EXECUTION's own words. That store outlives the pass and dies with
the Planner. This is the crossing — every plan found for a want no intention is already
walking, copied into the intentions store, one `execution:Intention` each.

**IT IS A COPY AND NOT A REWRITE**, which is why the search writes a step as `execution:Step`
in the first place: a translation on the way would be a second place the two shapes could
disagree. What the search added of its own — that the graph is a `planning:Plan`, which want
it is for, why the pass ended, what it was scored to spend — crosses with the rest and is
simply not read below. A lower layer does not have to understand every word it is handed; it
has to understand its own.

**A PLAN WITH NO STEPS DOES NOT CROSS.** It is an ANSWER — the want was already met, no lever
points at it, or none reached it inside the budget — and an answer is not a commitment. The
plan graph still holds it, and `planning:outcome` still says which; nothing stands among the
intentions for a want nobody is doing anything about.

**AND NOTHING HERE ABSORBS BY PATIENCE.** `Executor.commit` is the other door into the same copy,
and it refuses a second plan for a want it is already walking while that one is younger than
the agent's patience, superseding it after. This door refuses a second plan for a want being
walked at all: the plan graph of a want an intention pursues is still in the imaginarium, since
that outlives the pass, and it is not the pass's to hand down twice. A caller that wants the
amortisation asks the executor instead. Both are the executor's adoption, so what a committed
plan LOOKS like is settled in one place either way, and nothing but the executor writes the
intentions.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.store import Raw, bind, graphs_of, rows

from .ontology import PLAN_GRAPH

log = logging.getLogger("publish_plan")

#  WHICH WANT A PLAN IS FOR, off the plan's own root. A plan graph is named for its want and
#  the row says so; the read asks the row, because a name is for eyes.
_FOR_Q = """SELECT ?want WHERE { GRAPH $plan { $plan planning:for ?want } }"""


def publish_plan(imaginarium: ox.Store, executor) -> list[str]:
    """Hand every plan the pass left in `imaginarium` to `executor`. The intentions minted.

    The plans are asked for BY CLASS — `planning:PlanGraph`, whatever the pass named them —
    which is the same read every other door here makes and the reason a pass classifies what
    it writes.
    """
    minted = []
    walking = set(executor.walking())
    for graph in sorted(graphs_of(imaginarium, PLAN_GRAPH)):
        found = rows(imaginarium, bind(_FOR_Q, plan=Raw(f"<{graph}>")))
        if not found:
            #  A PLAN GRAPH THAT NAMES NO WANT is one nobody can carry out on anyone's behalf,
            #  and the intentions keep what an agent is doing and for what.
            log.error("%s: a plan graph names no want, so it cannot be committed: %s",
                      executor.id, graph)
            continue
        if found[0]["want"] in walking:
            #  THE IMAGINARIUM OUTLIVES THE PASS, so a plan an earlier pass found is still
            #  here while an intention walks it; handed down again it minted a second intention
            #  for one want every pass — measured, three passes, three intentions.
            continue
        intention = executor.commit(imaginarium, graph, found[0]["want"])
        if intention is not None:
            minted.append(intention)
    return minted

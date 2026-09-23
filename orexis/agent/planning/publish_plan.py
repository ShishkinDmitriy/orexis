"""Handing a pass's plans down — the last thing planning does, and the only thing it does to
another layer's store.

A pass writes what it found into the imaginarium it searched in: one `planning:PlanGraph` per
want, holding the steps in the LEDGER's own words. That store is memory and dies with the
pass. This is the crossing — every plan the pass wrote, copied into the intentions store, one
`execution:Intention` each.

**IT IS A COPY AND NOT A REWRITE**, which is why the search writes a step as `execution:Step`
in the first place: a translation on the way would be a second place the two shapes could
disagree. What the search added of its own — that the graph is a `planning:Plan`, which want
it is for, why the pass ended, what it was scored to spend — crosses with the rest and is
simply not read below. A lower layer does not have to understand every word it is handed; it
has to understand its own.

**A PLAN WITH NO STEPS DOES NOT CROSS.** It is an ANSWER — the want was already met, no lever
points at it, or none reached it inside the budget — and an answer is not a commitment. The
plan graph still holds it, and `planning:outcome` still says which; nothing stands in the
ledger for a want nobody is doing anything about.

**AND NOTHING HERE ABSORBS.** `Keeper.commit` is the other door into the same copy, and it
refuses a second plan for a want it is already walking while that one is younger than the
agent's patience. This door does not: it is the pass handing down what it found, and a caller
that wants the amortisation asks the keeper instead. Both end in `plans.copy_plan`, so what a
committed plan LOOKS like is settled in one place either way.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from orexis.agent.execution.plans import copy_plan
from orexis.agent.store import Raw, bind, graphs_of, rows

from .ontology import PLAN_GRAPH

log = logging.getLogger("publish_plan")

#  WHICH WANT A PLAN IS FOR, off the plan's own root. A plan graph is named for its want and
#  the row says so; the read asks the row, because a name is for eyes.
_FOR_Q = """SELECT ?want WHERE { GRAPH $plan { $plan planning:for ?want } }"""


def publish_plan(imaginarium: ox.Store, intentions: ox.Store, agent_id: str) -> list[str]:
    """Copy every plan the pass left in `imaginarium` into `intentions`. The intentions minted.

    The plans are asked for BY CLASS — `planning:PlanGraph`, whatever the pass named them —
    which is the same read every other door here makes and the reason a pass classifies what
    it writes.
    """
    minted = []
    for graph in sorted(graphs_of(imaginarium, PLAN_GRAPH)):
        found = rows(imaginarium, bind(_FOR_Q, plan=Raw(f"<{graph}>")))
        if not found:
            #  A PLAN GRAPH THAT NAMES NO WANT is one nobody can carry out on anyone's behalf,
            #  and the ledger keeps what an agent is doing and for what.
            log.error("%s: a plan graph names no want, so it cannot be committed: %s",
                      agent_id, graph)
            continue
        intention = copy_plan(imaginarium, graph, intentions, agent_id, found[0]["want"])
        if intention is not None:
            minted.append(intention)
    return minted

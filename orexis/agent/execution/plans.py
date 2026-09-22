"""Copying a found plan into the ledger — the one act between deciding and remembering.

The search writes a plan into a store of its own: a graph per want, holding one
`execution:Step` per step in the ledger's own words, chained by `execution:then`. This takes
that graph and puts it in the intentions store under an `execution:Intention` — adopted now,
standing at its first step, pursuing the want it was found for.

**IT IS A COPY AND NOT A REWRITE**, and that is why the search writes the steps in this
layer's vocabulary rather than its own: a translation on the way would be a second place the
two shapes could disagree, and the shape a step is written in is the shape a step is read in.
What the search adds of its own — that this is a `planning:Plan` and which want it is for —
crosses with the rest and is simply not read here. A lower layer does not have to understand
every word it is handed; it has to understand its own.

**QUADS AND NOT TEXT.** A serialise-and-reparse relabels blank nodes, so a step's own node
would come out the far side unequal to the one the plan names. The same trap the imaginarium's
filling exists for, at the other end of the pass.

See knowledge/decisions/an-intention-is-a-plan-committed-to.md.
"""

from __future__ import annotations

import logging
import uuid

import pyoxigraph as ox

from orexis.agent import clock
from orexis.agent.ontology import OREXIS
from .ontology import EXECUTION, intentions_graph
from orexis.agent.store import add_quads, quads, rows

log = logging.getLogger("plans")

_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_XSD_DATETIME = ox.NamedNode("http://www.w3.org/2001/XMLSchema#dateTime")

INTENTION = EXECUTION + "Intention"
#  The head a standing intention is AT — not the whole plan, which `execution:step` names, and
#  not the first step for ever: what `by` points at moves as the world answers each step.
BY = EXECUTION + "by"
STEP = EXECUTION + "step"
PURSUES = EXECUTION + "pursues"
ADOPTED_AT = EXECUTION + "adoptedAt"
RESOLVED_AT = EXECUTION + "resolvedAt"
OUTCOME = EXECUTION + "outcome"

#  THE HEAD OF A PLAN is the step nothing else points `execution:then` at — read rather than
#  written, since the chain already says it and a second statement of the same fact is a
#  second thing to keep true.
_HEAD_Q = """
SELECT ?step WHERE {
  GRAPH $plan {
    ?step a execution:Step ; execution:partOf $root .
    FILTER NOT EXISTS { ?other execution:then ?step } } }"""

_STEPS_Q = """
SELECT ?step WHERE { GRAPH $plan { ?step a execution:Step ; execution:partOf $root } }"""


def copy_plan(source: ox.Store, graph: str, intentions: ox.Store, agent_id: str,
              want: str) -> str | None:
    """Copy the plan in `graph` of `source` into `agent_id`'s ledger. The intention, or None.

    None for an empty plan, which is an answer and not a commitment: the search reached the
    want's met state in no steps, so there is nothing to carry out and nothing to stand.

    The intention is adopted at the clock's instant, stands at the plan's HEAD and names the
    want it pursues. Nothing decides here — whoever found the plan decided, and this keeps the
    record honest (an-intention-is-a-plan-committed-to).
    """
    from orexis.agent.store import bind, Raw
    named = Raw(f"<{graph}>")
    node = ox.NamedNode(intentions_graph(agent_id))
    steps = [r["step"] for r in rows(source, bind(_STEPS_Q, plan=named, root=named))]
    if not steps:
        log.debug("%s: the plan for %s has no steps — nothing to commit", agent_id, want)
        return None
    head = [r["step"] for r in rows(source, bind(_HEAD_Q, plan=named, root=named))]
    if len(head) != 1:
        raise RuntimeError(
            f"the plan in <{graph}> has {len(head)} heads — a plan is a chain, and a chain "
            "has one step nothing follows")

    #  THE STEPS THEMSELVES, quad for quad, into the ledger's graph. Everything the plan graph
    #  holds crosses: the steps, their fillings, the chain, and whatever the layer above wrote
    #  about the plan. What this layer does not read, it also does not drop.
    add_quads(intentions, (ox.Quad(q.subject, q.predicate, q.object, node)
                           for q in quads(source, graph)))

    intention = ox.NamedNode(f"{OREXIS}intention_{agent_id}_{uuid.uuid4().hex[:8]}")
    now = ox.Literal(clock.now().isoformat(), datatype=_XSD_DATETIME)
    own = [ox.Quad(intention, _RDF_TYPE, ox.NamedNode(INTENTION), node),
           ox.Quad(intention, ox.NamedNode(PURSUES), ox.NamedNode(want), node),
           ox.Quad(intention, ox.NamedNode(ADOPTED_AT), now, node),
           ox.Quad(intention, ox.NamedNode(BY), ox.NamedNode(head[0]), node)]
    own += [ox.Quad(intention, ox.NamedNode(STEP), ox.NamedNode(s), node) for s in sorted(steps)]
    add_quads(intentions, own)
    log.info("%s: committed a plan of %d step(s) for %s", agent_id, len(steps),
             want.rsplit("#", 1)[-1])
    return intention.value

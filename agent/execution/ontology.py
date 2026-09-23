"""The execution layer's own words (#529).

`execution:` for the intentions — what an intention is made of, and the one figure that governs
keeping. A term one layer reads and writes carries that layer's prefix, so a reader of any
query can tell which layer it speaks for; what EVERY layer writes in stays `orexis:` and lives
beside them, in `agent.ontology`.

THESE SAT IN THE SHARED FILE, and its `.ttl` beside it — which declared twenty-seven
`execution:` terms and not one `orexis:` one, so the file both layers imported for the kernel's
vocabulary was carrying only this layer's. The `LAYER_OF` table that decided which namespace a
name belonged to went with them: it had no reader, and `term()` consulted it for one call.
"""

from __future__ import annotations

EXECUTION = "http://example.org/orexis/execution#"

#  HOW LONG A COMMITMENT IS GIVEN before a fresh impulse to do the same thing is decided
#  again — the one figure of execution's that something outside it reads: a want
#  foreseen at an instant holds until that instant plus this, because the last step is placed
#  AT the instant and its verdict comes after.
PATIENCE_S = EXECUTION + "patienceS"

_GRAPH = "http://example.org/orexis/graph/"


def intentions_graph(agent_id: str) -> str:
    """What this agent is committed to, standing and resolved. Its own, and only its own.

    NOT public, and the absence is the design: an intention disclosed is strategy leaked. Apart
    from the picks graph on purpose — a pick has one value, held to `sh:maxCount 1`, while
    intentions accumulate a history: every resolved one stays, with its outcome and its reason,
    because intentions that forgot their resolutions could not answer the only question an operator
    brings to it, which is what this agent thought it was doing and why it stopped.
    """
    return _GRAPH + "intentions/" + agent_id

"""Where an agent keeps what it owes — its own graph, named from its own id.

PRIVATE, on the intention ledger's precedent and for its reason. A desire graph is public
because a region is arithmetic over ranges the world states; an obligation is neither: it
ACCUMULATES at runtime, and every public graph is replaced from the ratified files at boot,
so a public obligation would be forgotten every restart — which is exactly the defect this
persistence exists to end. Disclosure comes the way an intention's does: the sovereign asks.
"""

from __future__ import annotations

from agent.ontology import GRAPH_PREFIX

_OBLIGATIONS = GRAPH_PREFIX + "obligations/"


def obligations_graph(agent_id: str) -> str:
    """What this agent owes, standing and discharged. Its own, and only its own."""
    return _OBLIGATIONS + agent_id

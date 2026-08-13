"""The one graph this capability owns, named from the one identifier a process is given.

Here rather than in `agent/ontology.py` for the reason that file states about itself: everything
in it is true of *every* capability, and this is true of one. A graph an agent without a stake
and a lever never has is not kernel furniture.

NOT public, and the absence is the design: an intention disclosed is strategy leaked. The bid is
the public face of an intention to acquire — the market sees what you do, never what you are
trying to bring about. Like the beliefs graph, it is reachable only by naming it, which is what
keeps this module's write boundary checkable.

Apart from the beliefs graph on purpose, exactly as revisions are: a belief has one value, held
to `sh:maxCount 1`, while intentions accumulate a history — every resolved one stays, with its
outcome and its reason, because a ledger that forgot its resolutions could not answer the only
question an operator brings to it: what did this agent think it was doing, and why did it stop.
"""

from __future__ import annotations

from agent.ontology import GRAPH_PREFIX

_INTENTIONS = GRAPH_PREFIX + "intentions/"


def intentions_graph(agent_id: str) -> str:
    """What this agent is committed to, standing and resolved. Its own, and only its own."""
    return _INTENTIONS + agent_id

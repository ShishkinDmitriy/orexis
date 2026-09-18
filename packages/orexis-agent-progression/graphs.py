"""The private graphs a mind keeps, named from the one identifier a process is given.

This lived in the intention package and said it was here "rather than in the kernel
vocabulary" — `agent/ontology.py` then, `ontology.py` beside this file since #451 — because a
graph an agent without a stake and a lever never has is not kernel furniture. Every
agent keeps a ledger now — commitment is not plug-in-able — so the reason has expired and the
file has moved. It stays apart from `ontology.py` for that file's own stated reason: what is in
there is a TERM, and a graph IRI is an instance built from an agent's own id.

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

from .ontology import graph_prefix, term


def intentions_graph(agent_id: str) -> str:
    """What this agent is committed to, standing and resolved. Its own, and only its own."""
    return graph_prefix(term("IntentionGraph")) + agent_id

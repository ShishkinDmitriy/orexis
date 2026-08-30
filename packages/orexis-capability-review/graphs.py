"""The three graphs this capability owns, named from the one identifier a process is given.

Here rather than in `modality/ontology.py` for the reason that file states about itself: everything
in it is true of *every* capability, and these are true of one. A graph an agent without a
mandate never has is not kernel furniture.

Each is built from the agent's own id — the single instance identifier the rules allow a process
to name — exactly as `beliefs_graph` is. The prefix comes from the kernel because where a graph
lives in the IRI space is not this package's business; what it holds is.
"""

from __future__ import annotations

from modality.ontology import GRAPH_PREFIX

_REVISIONS = GRAPH_PREFIX + "revisions/"
_EVIDENCE = GRAPH_PREFIX + "evidence/"
_SUMMARIES = GRAPH_PREFIX + "summaries/"


def revisions_graph(agent_id: str) -> str:
    """What this agent has decided about itself, and when each is worth revisiting.

    Apart from the beliefs graph on purpose. A belief has exactly one value — every capability's
    shapes say so with `sh:maxCount 1` — so a decision cannot live beside the value it replaced
    without making the agent fail its own validation.
    """
    return _REVISIONS + agent_id


def evidence_graph(agent_id: str) -> str:
    """The reviewer's scratch, rebuilt at every arising. Nothing else ever reads it."""
    return _EVIDENCE + agent_id


def summaries_graph(agent_id: str) -> str:
    """What this agent's readings came to — running totals, not readings.

    Apart from `:sensed` deliberately, and the separation is what makes the write boundary
    checkable: `:sensed` is the measurement record, written by whatever observed and NEVER by a
    review, while a summary is the agent's own derived account of its past and is rolled over
    every time it arises. Keeping them in one graph would have made "a review does not touch the
    sensed record" untestable, and an invariant nothing can check is a comment.
    """
    return _SUMMARIES + agent_id

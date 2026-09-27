"""Everything revision reports of how it is doing — its gauge and its event — and nowhere else.

Instrumentation, not model (`agent/metrics.py`). Adding a figure is editing this module.

THE GAUGE IS OVER THE BELIEF BASE, off its catalogue, where `revise` describes every revision
graph it writes (knowledge/domain/belief/revision.md).
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.metrics import Event, Gauge, sample

from .ontology import REVISION_GRAPH, SETTLED

#  THE REVISIONS, and how many a budget cut short — settled false, which the next pass continues.
#  A revision that stays unsettled window after window is a rule set that never settles. The words
#  are spelled from `ontology.py`, since the store's dictionary binds no label to this package's.
REVISIONS = Gauge("revisions", f"""
SELECT (COUNT(?g) AS ?revisions) (SUM(IF(?settled, 0, 1)) AS ?unsettled)
WHERE {{ GRAPH $cat {{ ?g a <{REVISION_GRAPH}> ; <{SETTLED}> ?settled }} }}""")

#  EACH REVISION PASS, by the deliberator: the sources it was handed, the rule executions it spent,
#  how many it left cut short for the next pass, and its real seconds.
REVISE = Event("revise", values=("sources", "executions", "cut", "duration_s"))


def gauges(beliefs: ox.Store) -> list:
    """Revision's gauge, sampled over the belief base."""
    return sample(__name__, [beliefs])

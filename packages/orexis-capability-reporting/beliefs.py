"""What a reporting agent must believe. Declared here, next to the code that reads it.

One figure, and it is required. What used to make this block special was that it was read with
`read_optional` — its absence meant the agent reported nothing, which put "is this agent
observable at all" in a private file where no shape and no peer could read the answer. Every
agent reports now, so the only question left is how often, and that is an ordinary required
parameter like any other capability's.

Vocabulary: capabilities/reporting/ontology.ttl. Rules: capabilities/reporting/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from orexis_modality_graph.beliefs import Picks

from .terms import STORING, term


@dataclass(frozen=True)
class ReportingBeliefs:
    """How often this agent puts its account of itself somewhere.

    A rate belongs in beliefs for the same reason the sensing cadence does: a test world may want
    it faster than a deployed one, and that is the agent's own parameter rather than the world's
    topology.
    """

    interval_s: int


REPORTING_PICKS = Picks(
    capability=STORING,
    cls=ReportingBeliefs,
    terms={"interval_s": term("metricsIntervalS")},
)

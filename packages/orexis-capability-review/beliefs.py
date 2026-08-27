"""What a reviewing agent must believe. Declared here, next to the code that reads it.

One figure, and it is a floor rather than a schedule. What used to make this block special was
that it was read with `read_optional` — its absence meant the agent never reviewed at all, which
made a private file the switch for a public ability. The switch is now the mandate, in the world,
so this is an ordinary required parameter like any other capability's.

Vocabulary: capabilities/review/ontology.ttl. Rules: capabilities/review/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.beliefs import Picks


from .terms import RECKONING, term


@dataclass(frozen=True)
class ReviewBeliefs:
    """How often an agent is willing to reconsider — at the most.

    Not the schedule. A decision knows when its own effect could show, and plans the next arising
    from that; this only stops one planning something absurdly soon.
    """

    interval_s: int


REVIEW_PICKS = Picks(
    capability=RECKONING,
    cls=ReviewBeliefs,
    terms={"interval_s": term("reviewIntervalS")},
)

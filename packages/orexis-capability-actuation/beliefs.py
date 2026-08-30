"""What an actuating agent must believe. Declared here, next to the code that reads it.

One figure, and it is about **waiting** rather than about dosing. Everything that decides how
much water flows is on the device — its flow rate, its own hard cap — because those are facts
about hardware and belong in the world. What is left for the agent to believe is how long it
will wait for that hardware to say it did the thing.

The same shape as `sensing:readingGraceS`, deliberately. There the agent chooses the
interval, so staleness is that interval plus slack; here the agent computes the open-seconds
from the device's own calibration, so lateness is that duration plus slack. In both cases an
absolute deadline would contradict the agent's own instruction.

Vocabulary: capabilities/actuation/ontology.ttl. Rules: capabilities/actuation/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from orexis_deliberation.beliefs import Picks

from .terms import ACTUATION, term


@dataclass(frozen=True)
class ActuationBeliefs:
    """actuation:Actuation — how long to wait before saying a dose went unconfirmed.

    Not a timeout on the pour: nothing here interrupts a valve, and nothing here re-sends. It
    is the point after which silence stops being *probably still pouring* and starts being
    something worth reporting.
    """

    dose_grace_s: int


ACTUATION_PICKS = Picks(
    capability=ACTUATION,
    cls=ActuationBeliefs,
    terms={"dose_grace_s": term("doseGraceS")},
)

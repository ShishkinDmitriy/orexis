"""What a bidder and a host must believe — and, for the bidder, what it makes of a reading.

The judgment lives here rather than in perception on purpose: a band is a fact about a
*stake*, not about a sensor. The same number is trouble for a fern and comfort for a
succulent, so the agent that holds the target is the only one entitled to say which.

Vocabulary: capabilities/market/ontology.ttl (protocol) + domain/water/ontology.ttl (what a
bid means here). Rules: capabilities/market/shapes.ttl, domain/water/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.beliefs import Block

from .terms import BIDDING, HOSTING

BANDS = ("LOW", "OK", "HIGH")


@dataclass(frozen=True)
class BiddingBeliefs:
    """ag:Bidding — its wallet, its desire, its limits, and its private value curve."""

    endowment: float
    target: float
    low: float
    high: float
    litres_per_fraction: float
    max_value_per_l: float

    def band(self, value: float) -> str:
        """A reading judged against MY limits. Never stored — always recomputed."""
        if value < self.low:
            return "LOW"
        if value > self.high:
            return "HIGH"
        return "OK"

    def urgency(self, value: float) -> float:
        """How close this reading puts me to trouble: 0.0 at my ceiling, 1.0 at my floor.

        This is what an agent means by "watch me more closely" — so it is what perception is
        given when it asks. A band with no span is all-or-nothing trouble.
        """
        span = self.high - self.low
        if span <= 0:
            return 1.0
        return min(1.0, max(0.0, (self.high - value) / span))


@dataclass(frozen=True)
class HostingBeliefs:
    """ag:Hosting — the seller's terms and the shape of a round."""

    quantity_l: float
    reserve_price_per_l: float
    bid_window_s: int
    cooldown_s: int


BIDDING_BLOCK = Block(
    capability=BIDDING,
    cls=BiddingBeliefs,
    terms={
        "endowment": "hasEndowment",
        "target": "hasTarget",
        "low": "bandLow",
        "high": "bandHigh",
        "litres_per_fraction": "litresPerFraction",
        "max_value_per_l": "maxValuePerL",
    },
)

HOSTING_BLOCK = Block(
    capability=HOSTING,
    cls=HostingBeliefs,
    terms={
        "quantity_l": "offerQuantityL",
        "reserve_price_per_l": "reservePricePerL",
        "bid_window_s": "bidWindowS",
        "cooldown_s": "roundCooldownS",
    },
)

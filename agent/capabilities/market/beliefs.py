"""What a bidder and a host must believe — and, for the bidder, what it makes of a reading.

The judgment lives here rather than in perception on purpose: a band is a fact about a
*stake*, not about a sensor. The same number is trouble for a fern and comfort for a
succulent, so the agent that holds the target is the only one entitled to say which.

Vocabulary: capabilities/market/ontology.ttl (protocol) + domain/water/ontology.ttl (what a
bid means here). Rules: capabilities/market/shapes.ttl, domain/water/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent import ontology
from agent.beliefs import Block

from .terms import BIDDING, HOSTING, term

BANDS = ("LOW", "OK", "HIGH")


@dataclass(frozen=True)
class BiddingBeliefs:
    """market:Bidding — its wallet, its desire, its limits, and its private value curve."""

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
    """market:Hosting — the seller's terms and the shape of a round."""

    quantity_l: float
    reserve_price_per_l: float
    bid_window_s: int
    cooldown_s: int


BIDDING_BLOCK = Block(
    capability=BIDDING,
    cls=BiddingBeliefs,
    terms={
        # Two namespaces, and the split is which package DECLARES the term. The wallet is
        # the protocol's — how much a bidder brought to the venue. Everything under it is the
        # water domain's: what a bid is WORTH here, which a market for anything else would
        # answer differently. That split is visible now: swapping the domain swaps a namespace,
        # which is what AGENTS.md means by the domain being a plug-in.
        "endowment": term("hasEndowment"),
        "target": ontology.WATER + "hasTarget",
        "low": ontology.WATER + "bandLow",
        "high": ontology.WATER + "bandHigh",
        "litres_per_fraction": ontology.WATER + "litresPerFraction",
        "max_value_per_l": ontology.WATER + "maxValuePerL",
    },
)

HOSTING_BLOCK = Block(
    capability=HOSTING,
    cls=HostingBeliefs,
    terms={
        "quantity_l": term("offerQuantityL"),
        "reserve_price_per_l": term("reservePricePerL"),
        "bid_window_s": term("bidWindowS"),
        "cooldown_s": term("roundCooldownS"),
    },
)

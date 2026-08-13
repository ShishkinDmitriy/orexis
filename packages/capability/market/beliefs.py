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
    """market:Bidding — its wallet, the point it is aiming at, and its private value curve.

    **The band is not here any more, and its absence is the point.** A bidder used to hold
    `water:bandLow` and `water:bandHigh` and to be the only thing in an agent that could say what
    a reading MEANT — which made having an opinion about your own state conditional on being a
    market participant, and limited it to the one property a bid is priced in. Judging a reading
    is desire's, in `packages/capability/desire/`, where it is per property and deduced from what
    the world states rather than picked. What is left here is what a BID needs and nothing else:
    a wallet, a point to aim at, and what a litre is worth on the way to it.
    """

    endowment: float
    target: float
    litres_per_fraction: float
    max_value_per_l: float


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

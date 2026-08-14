"""What a bidder and a host must believe — and, for the bidder, what it makes of a reading.

The judgment lives here rather than in sensing on purpose: a band is a fact about a
*stake*, not about a sensor. The same number is trouble for a fern and comfort for a
succulent, so the agent that holds the target is the only one entitled to say which.

Vocabulary: capabilities/market/ontology.ttl (protocol) + domain/water/ontology.ttl (what a
bid means here). Rules: capabilities/market/shapes.ttl, domain/water/shapes.ttl.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.beliefs import Block

from .terms import BIDDING, HOSTING, term

BANDS = ("LOW", "OK", "HIGH")

# See the note inside BIDDING_BLOCK: the domain coupling is this package's, stated here.
_WATER = "http://example.org/agora/water#"


@dataclass(frozen=True)
class BiddingBeliefs:
    """market:Bidding — its wallet, the point it is aiming at, and its private value curve.

    **Neither the band nor the aim is here any more, and the absences are the point.** A bidder
    used to hold `water:bandLow`/`water:bandHigh` and `water:hasTarget`, making it the only
    thing in an agent that could say what a reading MEANT or what state it was steering for —
    which made both conditional on being a market participant. Judging is desire's; so is the
    aim, which any agent with a stake holds whether or not a market exists. What is left here is
    what only a BID needs: a wallet, how a deficit becomes litres, and what a litre is worth.
    The aim is asked of whoever provides the desire family, at bid time.
    """

    endowment: float
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
        # The one deliberately domain-coupled corner of this package: what a bid is WORTH is
        # the domain's to say, and the coupling is a literal here rather than a kernel
        # constant (#148) — the kernel names no domain, and a cross-package reference is an
        # IRI, exactly as terms.py already does for sensing and actuation.
        "litres_per_fraction": _WATER + "litresPerFraction",
        "max_value_per_l": _WATER + "maxValuePerL",
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

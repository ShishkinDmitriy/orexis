"""ag:PayAsBid — turn a lot and a set of bids into a proposed allocation.

This was `auction.propose_match`, a module-level function that `hosting.py` imported directly —
while `auction.py`'s own docstring called the format "a replaceable v1 choice". It was not
replaceable: swapping it meant editing that file, so the claimed seam was a claim only. Issue #66.

**What makes this a capability and not a function** is that given a lot and a set of bids there
is more than one defensible answer, and the choice is visible to everyone bidding: under
pay-as-bid a winner pays what it offered, so the honest strategy is to shade; under a uniform
price it pays the clearing price, so bidding your true value costs you nothing. The rule changes
what a rational participant should say. That is the test in AGENTS.md rule 2 — where the *how*
could differ, it is a capability.

**What stays outside it.** The host proposes and clearing disposes: this decides an allocation,
never whether it is permitted. Solvency, the constitution and identity are `clearing.py`'s, and
`auction.run_round` is the path between them — the same whichever rule runs, which is why it did
not move.

Vocabulary: capabilities/matching/ontology.ttl. Rules: capabilities/matching/rules.ru.
See knowledge/decisions/an-auction-format-is-a-capability.md.
"""

from __future__ import annotations

from typing import Iterable

from agent.market import EPS, Bid, Offer, Trade, TradeLine
from agent.module import Module

from .terms import PAY_AS_BID


class PayAsBidModule(Module):
    """Greedy and discriminatory: highest bids filled first, each paying its own price."""

    CAPABILITY = PAY_AS_BID
    name = "pay-as-bid"

    @staticmethod
    def propose_match(offer: Offer, bids: Iterable[Bid]) -> Trade:
        """Allocate the offered quantity among the bids and propose a Trade.

        Static because this rule reads nothing about the agent running it — a lot and a set of
        bids fully determine the answer, which is what makes it testable without a world and
        auditable without a trace. A rule that later needs the host's own beliefs can stop being
        static then; the family's contract is the signature, not the binding.

        Keep only bids at or above the reserve, fill them highest-price-first (deterministic
        tie-break by agent id), each up to its own max_qty capped by remaining supply, and each
        paying its own bid price — which is ≥ reserve. No sale when nothing clears the reserve.
        Deterministic; no LLM.

        The host respects its *own* terms here (supply and reserve). The hard constraints are
        clearing's to enforce; this only proposes.

        Unchanged from the function it replaces, deliberately: #66 is about there being somewhere
        to put a second rule, not about this one being wrong. The uncontested-round defect in it
        is #50 and is still open.
        """
        eligible = sorted(
            (b for b in bids
             if b.max_qty_l > EPS and b.max_price_per_l >= offer.reserve_price_per_l - EPS),
            key=lambda b: (-b.max_price_per_l, b.agent),
        )

        remaining = offer.quantity_l
        lines: list[TradeLine] = []
        for bid in eligible:
            if remaining <= EPS:
                break
            qty = min(bid.max_qty_l, remaining)
            lines.append(TradeLine(agent=bid.agent, qty_l=qty, price_per_l=bid.max_price_per_l))
            remaining -= qty

        return Trade(offer=offer, lines=tuple(lines))

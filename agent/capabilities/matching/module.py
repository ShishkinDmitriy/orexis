"""The two ways of turning a lot and a set of bids into a proposed allocation.

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

**Both walk the same demand curve and disagree only about the bill.** That is a fact about these
two rules and not about the family, so the walk is written out twice rather than shared. A third
rule need not allocate highest-first at all — pro-rata across everyone who cleared the reserve is
an ordinary answer — and a helper factored out today would encode an invariant the family does not
have. Ten duplicated lines are cheaper than a false abstraction, and the tests hold both to the
same allocation where they should agree.

Vocabulary: capabilities/matching/ontology.ttl. Rules: capabilities/matching/rules.ru.
See knowledge/decisions/an-auction-format-is-a-capability.md and
knowledge/decisions/uniform-price-dissolves-the-uncontested-round.md.
"""

from __future__ import annotations

from typing import Iterable

from agent.market import EPS, Bid, Offer, Trade, TradeLine
from agent.module import Module

from .terms import PAY_AS_BID, UNIFORM_PRICE


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


class UniformPriceModule(Module):
    """One clearing price for everyone: where demand met supply, floored at the reserve."""

    CAPABILITY = UNIFORM_PRICE
    name = "uniform-price"

    @staticmethod
    def propose_match(offer: Offer, bids: Iterable[Bid]) -> Trade:
        """Allocate as pay-as-bid does, then bill every winner the same clearing price.

        The allocation is identical — bids at or above the reserve, highest first, each capped by
        what is left. What differs is the price, and it is the **lowest accepted** bid: the one
        that was filling when supply ran out, which is where the demand curve crossed the lot.

        **Lowest accepted rather than highest rejected**, deliberately. With divisible quantities
        the marginal bidder is almost always *partially* filled, so its own price is both the
        lowest accepted and the highest rejected and the two coincide; they can only differ where
        the lot happens to exhaust exactly on a bid boundary. Lowest accepted is then the one that
        needs nothing tracked about what was excluded, and it is what a treasury auction means by
        its stop-out price.

        **The reserve is the floor, not a special case.** `clearing` starts there and is only
        raised if the walk actually exhausts the lot. So a round whose demand never reaches the
        lot is not detected and handled — it is simply a walk that never crossed supply, and the
        price stays where the curve began. That is the whole of why this rule has no
        contested-or-not test in it, and issue #50 has nothing left to fix here: two bidders whose
        combined demand fits are both filled in full and both pay the reserve, because nothing
        else could have happened.

        Static for the same reason pay-as-bid is: a lot and a set of bids fully determine the
        answer. Deterministic; no LLM.
        """
        eligible = sorted(
            (b for b in bids
             if b.max_qty_l > EPS and b.max_price_per_l >= offer.reserve_price_per_l - EPS),
            key=lambda b: (-b.max_price_per_l, b.agent),
        )

        remaining = offer.quantity_l
        filled: list[tuple[str, float]] = []
        clearing = offer.reserve_price_per_l
        for bid in eligible:
            if remaining <= EPS:
                break
            qty = min(bid.max_qty_l, remaining)
            filled.append((bid.agent, qty))
            remaining -= qty
            if remaining <= EPS:
                # Supply ran out on this bid, so this is the marginal one and its price is where
                # demand met the lot. Assigned inside the loop rather than after it because the
                # last bid REACHED is not the last bid filled when the lot runs out mid-list.
                clearing = bid.max_price_per_l

        return Trade(
            offer=offer,
            lines=tuple(TradeLine(agent=agent, qty_l=qty, price_per_l=clearing)
                        for agent, qty in filled),
        )

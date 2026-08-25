"""The auction: the path from bids to claims, however they were matched.

An auction is a **process** — it condenses when a resource becomes contested, allocates, and
dissolves. The market is the standing structure it happens inside; see knowledge/domain/market.md,
which said the opposite until #66 and had `market:Market` declared with three MQTT topics all along.

So this file keeps the process and lost the matching. `propose_match` — greedy pay-as-bid —
used to live here, under a docstring calling it "a replaceable v1 choice" while `hosting.py`
imported it directly, which made it exactly not that. It is now `capabilities/market/matching.py`: a
family with pay-as-bid and uniform price implemented, so a third way of matching is a class and
a line of `PROVIDES` rather than an edit to this file.

**What is left here is true of every way of matching**: propose, validate, issue. The host
proposes and clearing disposes — that ordering is the auction's, not any one member's, which is
why it did not move. `match` arrives as a callable so this stays honest about depending on
nothing but the shape of the answer.

See knowledge/domain/auction.md, knowledge/domain/bid-matching.md, knowledge/domain/round.md,
knowledge/decisions/clearing-as-validator.md, knowledge/decisions/bid-matching-is-a-capability.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .clearing import Validation, Claim, issue_claims, validate
from .trade import Bid, MarketState, Offer, Trade

# What a matching capability offers: a lot and the bids for it, in — a proposed allocation out.
# Named so this module can say what it needs without naming who provides it.
Match = Callable[[Offer, Iterable[Bid]], Trade]


@dataclass
class AuctionResult:
    """The full host → clearing path for one auction."""

    trade: Trade
    validation: Validation
    claims: list[Claim]  # empty unless the trade validated


def run_auction(offer: Offer, bids: Iterable[Bid], state: MarketState, auction_id: str,
              match: Match, redeem_window_s: float | None = None) -> AuctionResult:
    """Host proposes the match; clearing validates; claims issue only on a green light.

    The window is the VENUE's and arrives from the host, which is the only party that has read
    the market node. Optional here so a caller with no venue — every matcher test — still runs
    the path it is testing rather than being made to invent a deadline.
    """
    trade = match(offer, bids)
    result = validate(trade, state)
    claims = issue_claims(trade, auction_id, redeem_window_s) if result.ok else []
    return AuctionResult(trade=trade, validation=result, claims=claims)

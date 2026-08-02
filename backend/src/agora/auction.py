"""The host's side of the market: run the auction and *propose a match*.

In v1 the host is the supply-scarce [supplier]; it collects bids and proposes a Trade.
Clearing then validates and co-signs it — the host proposes, clearing disposes. The auction
*format* lives here (it's the host's strategy), and it is a replaceable v1 choice.

See knowledge/domain/supplier.md, knowledge/decisions/clearing-as-validator.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .clearing import Voucher, Validation, issue_vouchers, validate
from .market import EPS, Bid, MarketState, Offer, Trade, TradeLine


def propose_match(offer: Offer, bids: Iterable[Bid]) -> Trade:
    """Allocate the offered quantity among the bids and propose a Trade.

    v1 format — **greedy pay-as-bid**: keep only bids at or above the reserve, fill them
    highest-price-first (deterministic tie-break by agent id), each up to its own max_qty
    capped by remaining supply, and each paying its own bid price (which is ≥ reserve). No
    sale when nothing clears the reserve. Deterministic; no LLM.

    The host respects its *own* terms (supply + reserve). The hard constraints
    (constitution, solvency, identity) are clearing's to enforce — this only proposes.
    """
    eligible = sorted(
        (b for b in bids if b.max_qty_l > EPS and b.max_price_per_l >= offer.reserve_price_per_l - EPS),
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


@dataclass
class RoundResult:
    """The full host → clearing path for one round."""

    trade: Trade
    validation: Validation
    vouchers: list[Voucher]  # empty unless the trade validated


def run_round(offer: Offer, bids: Iterable[Bid], state: MarketState, round_id: str) -> RoundResult:
    """Host proposes the match; clearing validates; vouchers issue only on a green light."""
    trade = propose_match(offer, bids)
    result = validate(trade, state)
    vouchers = issue_vouchers(trade, round_id) if result.ok else []
    return RoundResult(trade=trade, validation=result, vouchers=vouchers)

"""Clearing — the thin, stake-free validator (a notary, not an allocator).

The host runs the auction and proposes a Trade; clearing checks it is well-formed and
co-signs it before settlement. It computes nothing about who *should* win — only whether
the proposed trade cheats. A pure predicate: `validate(trade, state) -> Validation`.

Checks (see knowledge/decisions/clearing-as-validator.md):
  identity · order-consistency · conservation · solvency · constitution

v1 note: vouchers are unsigned in-process objects — the JWS/co-signature is a v2 transport
change, not a logic change. See knowledge/decisions/authn-authz-capabilities.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from .market import EPS, MarketState, Trade


@dataclass
class Validation:
    ok: bool
    violations: list[str] = field(default_factory=list)


def validate(trade: Trade, state: MarketState) -> Validation:
    """Return whether the proposed trade violates any integrity invariant."""
    v: list[str] = []
    off = trade.offer

    # --- identity: every party is a certified id -------------------------------
    if off.supplier not in state.certified:
        v.append(f"uncertified supplier: {off.supplier!r}")
    for line in trade.lines:
        if line.agent not in state.certified:
            v.append(f"uncertified agent: {line.agent!r}")

    # --- no duplicate lines (one leg per buyer) --------------------------------
    seen: set[str] = set()
    for line in trade.lines:
        if line.agent in seen:
            v.append(f"duplicate line for {line.agent!r}")
        seen.add(line.agent)

    # --- order-consistency: each line within its buyer's signed bid, >= reserve --
    for line in trade.lines:
        if line.qty_l < -EPS:
            v.append(f"{line.agent}: negative qty {line.qty_l}")
        bid = state.bids.get(line.agent)
        if bid is None:
            v.append(f"no signed bid for {line.agent!r}")
            continue
        if line.qty_l > bid.max_qty_l + EPS:
            v.append(f"{line.agent}: qty {line.qty_l} exceeds bid max {bid.max_qty_l}")
        if line.price_per_l > bid.max_price_per_l + EPS:
            v.append(f"{line.agent}: price {line.price_per_l} exceeds bid max {bid.max_price_per_l}")
        if line.price_per_l < off.reserve_price_per_l - EPS:
            v.append(f"{line.agent}: price {line.price_per_l} below reserve {off.reserve_price_per_l}")

    # --- conservation: total allocated within the offered quantity -------------
    if trade.total_qty_l > off.quantity_l + EPS:
        v.append(f"over-allocation: {trade.total_qty_l} > offered {off.quantity_l}")

    # --- solvency: each buyer can pay its line ---------------------------------
    for line in trade.lines:
        bal = state.wallets.get(line.agent, 0.0)
        if line.cost > bal + EPS:
            v.append(f"{line.agent}: cost {line.cost} exceeds wallet {bal}")

    # --- constitution: tank capacity + per-agent rot headroom ------------------
    if trade.total_qty_l > state.limits.tank_capacity_l + EPS:
        v.append(f"exceeds tank capacity: {trade.total_qty_l} > {state.limits.tank_capacity_l}")
    for line in trade.lines:
        head = state.limits.rot_headroom_l.get(line.agent)
        if head is not None and line.qty_l > head + EPS:
            v.append(f"{line.agent}: qty {line.qty_l} past rot headroom {head}")

    return Validation(ok=not v, violations=v)


@dataclass(frozen=True)
class Voucher:
    """Settlement token (capability). v1: unsigned, in-process — the signature chain
    (order_sig / match_sig / val_sig) is added later without changing this shape.
    See knowledge/decisions/authn-authz-capabilities.md."""

    sub: str  # who
    scope: str  # what
    amount_l: float  # water leg
    debit: float  # credit leg
    auction_id: str  # binds to the auction it was won in, never to a bidding pass
    jti: str  # anti-replay id


def issue_vouchers(trade: Trade, auction_id: str) -> list[Voucher]:
    """Turn a *validated* trade into per-buyer settlement vouchers. Caller must have
    confirmed `validate(trade, state).ok` first."""
    return [
        Voucher(
            sub=line.agent,
            scope=f"actuate:valve/{line.agent}",
            amount_l=line.qty_l,
            debit=line.cost,
            auction_id=auction_id,
            jti=uuid4().hex,
        )
        for line in trade.lines
    ]


def clear(trade: Trade, state: MarketState, auction_id: str) -> list[Voucher]:
    """Validate then issue vouchers; raise if the trade is invalid."""
    result = validate(trade, state)
    if not result.ok:
        raise ValueError("invalid trade: " + "; ".join(result.violations))
    return issue_vouchers(trade, auction_id)

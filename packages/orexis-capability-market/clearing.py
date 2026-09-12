"""Clearing — the thin, stake-free validator (a notary, not an allocator).

The host runs the auction and proposes a Trade; clearing checks it is well-formed and
co-signs it before settlement. It computes nothing about who *should* win — only whether
the proposed trade cheats. A pure predicate: `validate(trade, state) -> Validation`.

Checks (see knowledge/decisions/clearing-as-validator.md):
  identity · order-consistency · conservation · solvency · constitution

v1 note: claims are unsigned in-process objects — the JWS/co-signature is a v2 transport
change, not a logic change. See knowledge/decisions/authn-authz-capabilities.md.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import uuid4

from orexis_agent_progression.commitment import Commitment

from .trade import EPS, MarketState, Trade


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

    # --- constitution: total ≤ the lot, and each line within its own ceiling (#270) ------
    if trade.total_qty_l > state.limits.tank_capacity_l + EPS:
        v.append(f"exceeds tank capacity: {trade.total_qty_l} > {state.limits.tank_capacity_l}")
    for line in trade.lines:
        ceiling = state.limits.allocation_ceiling_l.get(line.agent)
        if ceiling is not None and line.qty_l > ceiling + EPS:
            v.append(f"{line.agent}: qty {line.qty_l} past allocation ceiling {ceiling}")

    return Validation(ok=not v, violations=v)


@dataclass(frozen=True, kw_only=True)
class Claim(Commitment):
    """Settlement token: the market's embodiment of a commitment (settlement-speaks-rea).

    The flow itself — who, what, how much, which round, once — is the kernel's `Commitment`,
    which is what a valve fulfils; this adds the CREDIT leg. The signature chain
    (match_sig / val_sig) rides on the wire, not on this shape. See
    knowledge/decisions/authn-authz-capabilities.md.
    """

    debit: float      # the credit leg
    #  FROM WHEN it may be presented (#625): the instant the winner's bid asked for, or None
    #  for a claim usable at once. `exp` is this plus the venue's window.
    usable_from: float | None = None


def issue_claims(trade: Trade, auction_id: str,
                 redeem_window_s: float | None = None, act_for=None,
                 wanted_at: dict | None = None) -> list[Claim]:
    """Turn a *validated* trade into per-buyer settlement claims. Caller must have
    confirmed `validate(trade, state).ok` first.

    Every claim from one auction shares an expiry, computed ONCE here rather than per line:
    the window runs from the moment the society allocated the good, so two winners of the
    same round are held for the same time and neither can be late by an accident of loop
    order. A `None` window leaves `exp` unset — see the field.

    `act_for(line, expires)` is the host's: the Serving act each claim is a commitment TO —
    this venue, so many litres, for this buyer, not after `expires`. Clearing does not know
    the host's lever, so it asks rather than inventing one; None leaves the act unset, which
    is what a matcher test with no venue gets.
    """
    #  A WINNER RECEIVES WATER AT A TIME (#625): where its bid asked for an instant, the
    #  window runs from THAT instant — the claim is usable from it, expires the window after
    #  it — and the shared expiry above is the case of nobody asking.
    now = time.time()
    wanted_at = wanted_at or {}
    out = []
    for line in trade.lines:
        usable_from = wanted_at.get(line.agent)
        opens = usable_from if usable_from is not None and usable_from > now else now
        expires = opens + redeem_window_s if redeem_window_s is not None else None
        out.append(Claim(
            sub=line.agent,
            permits=f"actuate:valve/{line.agent}",
            amount_l=line.qty_l,
            debit=line.cost,
            auction_id=auction_id,
            jti=uuid4().hex,
            exp=expires,
            usable_from=usable_from if usable_from is not None and usable_from > now else None,
            step=act_for(line, expires) if act_for is not None else None,
        ))
    return out


def clear(trade: Trade, state: MarketState, auction_id: str,
          redeem_window_s: float | None = None) -> list[Claim]:
    """Validate then issue claims; raise if the trade is invalid."""
    result = validate(trade, state)
    if not result.ok:
        raise ValueError("invalid trade: " + "; ".join(result.violations))
    return issue_claims(trade, auction_id, redeem_window_s)

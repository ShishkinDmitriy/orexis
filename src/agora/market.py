"""Market data model: signed orders, the host's proposed trade, and the state
clearing needs to validate it.

Vocabulary follows knowledge/decisions/clearing-as-validator.md — an *order* is a bid
(buyer) or ask (seller); the *host* proposes a *trade* (the match); *clearing* validates.
v1 is the supply-scarce case, so orders here are buyer bids and the host is the supplier.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tolerance for float comparisons (litres / credits are continuous).
EPS = 1e-9


@dataclass(frozen=True)
class Bid:
    """A buyer's signed order: willing to pay up to max_price_per_l for up to max_qty_l."""

    agent: str
    max_qty_l: float
    max_price_per_l: float


@dataclass(frozen=True)
class Offer:
    """The host/supplier's announced terms for the round (its signed ask side)."""

    supplier: str
    quantity_l: float
    reserve_price_per_l: float


@dataclass(frozen=True)
class TradeLine:
    """One buyer's leg of the proposed trade: qty at a cleared price."""

    agent: str
    qty_l: float
    price_per_l: float

    @property
    def cost(self) -> float:
        return self.qty_l * self.price_per_l


@dataclass(frozen=True)
class Trade:
    """The match the host proposes: who gets how much, at what price."""

    offer: Offer
    lines: tuple[TradeLine, ...]

    @property
    def total_qty_l(self) -> float:
        return sum(line.qty_l for line in self.lines)


@dataclass(frozen=True)
class Limits:
    """Constitution constraints — hard, non-negotiable. See knowledge/domain/constitution.md."""

    tank_capacity_l: float
    rot_headroom_l: dict[str, float]  # agent -> max additional L before root-rot


@dataclass(frozen=True)
class MarketState:
    """Everything clearing needs to validate a proposed trade (no auction logic here)."""

    bids: dict[str, Bid]  # agent -> their signed bid
    wallets: dict[str, float]  # agent -> credit balance
    certified: frozenset[str]  # valid ids (agents + supplier)
    limits: Limits

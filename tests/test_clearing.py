"""Tests for the clearing validator (a pure predicate — no infra, no LLM)."""

import dataclasses

import pytest

from agent.clearing import clear, issue_claims, validate
from agent.market import Bid, Limits, MarketState, Offer, Trade, TradeLine


def base_state() -> MarketState:
    """Two solvent, certified buyers with generous rot headroom; 5 L tank."""
    return MarketState(
        bids={
            "fern": Bid("fern", max_qty_l=3.0, max_price_per_l=0.50),
            "tomato": Bid("tomato", max_qty_l=4.0, max_price_per_l=0.60),
        },
        wallets={"fern": 100.0, "tomato": 100.0},
        certified=frozenset({"supplier", "fern", "tomato"}),
        limits=Limits(tank_capacity_l=5.0, rot_headroom_l={"fern": 3.0, "tomato": 4.0}),
    )


def base_offer() -> Offer:
    return Offer(supplier="supplier", quantity_l=5.0, reserve_price_per_l=0.20)


def trade_with(*lines: TradeLine) -> Trade:
    return Trade(offer=base_offer(), lines=lines)


# --- the happy path --------------------------------------------------------

def test_valid_trade_passes():
    trade = trade_with(
        TradeLine("tomato", qty_l=4.0, price_per_l=0.40),
        TradeLine("fern", qty_l=1.0, price_per_l=0.40),
    )
    result = validate(trade, base_state())
    assert result.ok, result.violations


def test_empty_trade_is_valid():
    # No sale is a legitimate outcome (all bids below reserve, etc.).
    assert validate(trade_with(), base_state()).ok


# --- identity --------------------------------------------------------------

def test_uncertified_agent_rejected():
    trade = trade_with(TradeLine("ghost", qty_l=1.0, price_per_l=0.40))
    result = validate(trade, base_state())
    assert not result.ok
    assert any("uncertified agent" in x for x in result.violations)


def test_uncertified_supplier_rejected():
    state = base_state()
    trade = Trade(
        offer=Offer(supplier="impostor", quantity_l=5.0, reserve_price_per_l=0.20),
        lines=(TradeLine("fern", 1.0, 0.40),),
    )
    result = validate(trade, state)
    assert not result.ok
    assert any("uncertified supplier" in x for x in result.violations)


# --- order-consistency -----------------------------------------------------

def test_qty_over_bid_rejected():
    trade = trade_with(TradeLine("fern", qty_l=3.5, price_per_l=0.40))  # bid max 3.0
    result = validate(trade, base_state())
    assert not result.ok
    assert any("exceeds bid max" in x for x in result.violations)


def test_price_over_bid_rejected():
    trade = trade_with(TradeLine("fern", qty_l=1.0, price_per_l=0.60))  # bid max 0.50
    assert not validate(trade, base_state()).ok


def test_price_below_reserve_rejected():
    trade = trade_with(TradeLine("fern", qty_l=1.0, price_per_l=0.10))  # reserve 0.20
    result = validate(trade, base_state())
    assert not result.ok
    assert any("below reserve" in x for x in result.violations)


def test_no_signed_bid_rejected():
    state = dataclasses.replace(base_state(), bids={"tomato": base_state().bids["tomato"]})
    # certify fern so we isolate the missing-bid check, not identity
    state = dataclasses.replace(state, certified=frozenset({"supplier", "fern", "tomato"}))
    trade = trade_with(TradeLine("fern", qty_l=1.0, price_per_l=0.40))
    result = validate(trade, state)
    assert not result.ok
    assert any("no signed bid" in x for x in result.violations)


def test_duplicate_line_rejected():
    trade = trade_with(
        TradeLine("fern", qty_l=1.0, price_per_l=0.40),
        TradeLine("fern", qty_l=1.0, price_per_l=0.40),
    )
    result = validate(trade, base_state())
    assert not result.ok
    assert any("duplicate line" in x for x in result.violations)


# --- conservation ----------------------------------------------------------

def test_over_allocation_rejected():
    trade = trade_with(
        TradeLine("tomato", qty_l=4.0, price_per_l=0.40),
        TradeLine("fern", qty_l=2.0, price_per_l=0.40),  # total 6 > offered 5
    )
    result = validate(trade, base_state())
    assert not result.ok
    assert any("over-allocation" in x for x in result.violations)


# --- solvency --------------------------------------------------------------

def test_insolvent_buyer_rejected():
    state = dataclasses.replace(base_state(), wallets={"fern": 0.30, "tomato": 100.0})
    trade = trade_with(TradeLine("fern", qty_l=3.0, price_per_l=0.40))  # cost 1.20 > 0.30
    result = validate(trade, state)
    assert not result.ok
    assert any("exceeds wallet" in x for x in result.violations)


# --- constitution ----------------------------------------------------------

def test_exceeds_tank_capacity_rejected():
    # Raise the offer above tank so conservation passes but the constitution catches it.
    state = dataclasses.replace(base_state(), limits=Limits(tank_capacity_l=3.0, rot_headroom_l={"tomato": 4.0}))
    trade = Trade(
        offer=Offer(supplier="supplier", quantity_l=5.0, reserve_price_per_l=0.20),
        lines=(TradeLine("tomato", qty_l=4.0, price_per_l=0.40),),
    )
    result = validate(trade, state)
    assert not result.ok
    assert any("tank capacity" in x for x in result.violations)


def test_past_rot_headroom_rejected():
    state = dataclasses.replace(base_state(), limits=Limits(tank_capacity_l=5.0, rot_headroom_l={"fern": 0.5, "tomato": 4.0}))
    trade = trade_with(TradeLine("fern", qty_l=2.0, price_per_l=0.40))  # headroom 0.5
    result = validate(trade, state)
    assert not result.ok
    assert any("rot headroom" in x for x in result.violations)


# --- claims / clear() ------------------------------------------------------

def test_clear_issues_grants_for_valid_trade():
    trade = trade_with(
        TradeLine("tomato", qty_l=4.0, price_per_l=0.40),
        TradeLine("fern", qty_l=1.0, price_per_l=0.40),
    )
    claims = clear(trade, base_state(), auction_id="R-1")
    assert {g.sub for g in claims} == {"tomato", "fern"}
    tomato = next(g for g in claims if g.sub == "tomato")
    assert tomato.amount_l == 4.0
    assert tomato.debit == pytest.approx(1.60)  # 4.0 * 0.40
    assert tomato.scope == "actuate:valve/tomato"
    assert len({g.jti for g in claims}) == 2  # unique anti-replay ids


def test_clear_raises_on_invalid_trade():
    trade = trade_with(TradeLine("fern", qty_l=99.0, price_per_l=0.40))
    with pytest.raises(ValueError, match="invalid trade"):
        clear(trade, base_state(), auction_id="R-1")

"""Tests for the clearing validator (a pure predicate — no infra, no LLM)."""

import dataclasses

import pytest

from packages.capability.market.clearing import clear, issue_claims, validate
from packages.capability.market.trade import Bid, Limits, MarketState, Offer, Trade, TradeLine


def base_state() -> MarketState:
    """Two solvent, certified buyers with generous allocation ceilings; 5 L tank."""
    return MarketState(
        bids={
            "fern": Bid("fern", max_qty_l=3.0, max_price_per_l=0.50),
            "tomato": Bid("tomato", max_qty_l=4.0, max_price_per_l=0.60),
        },
        wallets={"fern": 100.0, "tomato": 100.0},
        certified=frozenset({"supplier", "fern", "tomato"}),
        limits=Limits(tank_capacity_l=5.0, allocation_ceiling_l={"fern": 3.0, "tomato": 4.0}),
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
    state = dataclasses.replace(base_state(), limits=Limits(tank_capacity_l=3.0, allocation_ceiling_l={"tomato": 4.0}))
    trade = Trade(
        offer=Offer(supplier="supplier", quantity_l=5.0, reserve_price_per_l=0.20),
        lines=(TradeLine("tomato", qty_l=4.0, price_per_l=0.40),),
    )
    result = validate(trade, state)
    assert not result.ok
    assert any("tank capacity" in x for x in result.violations)


def test_past_the_allocation_ceiling_rejected():
    state = dataclasses.replace(base_state(), limits=Limits(tank_capacity_l=5.0, allocation_ceiling_l={"fern": 0.5, "tomato": 4.0}))
    trade = trade_with(TradeLine("fern", qty_l=2.0, price_per_l=0.40))  # headroom 0.5
    result = validate(trade, state)
    assert not result.ok
    assert any("allocation ceiling" in x for x in result.violations)


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


# --- the ceiling is POPULATED, not merely checked (#270) -----------------------------------------


def test_a_world_whose_plants_state_survival_ranges_yields_ceilings():
    """The half that was missing for as long as the check existed.

    `clearing.py` has always refused a line past a participant's ceiling, and the only
    production caller passed `{}` — so `.get()` returned None for every agent and the branch was
    skipped for every line of every trade. The unit test above passes a populated map and is
    correct; it proves the CHECK. Nothing asserted that anything FILLS it, which is
    `a-test-that-asserted-nothing` one level up: not an assertion that never ran, but a production
    input that was always empty.

    So this asserts the derivation reaches the map, per world, and that the numbers are the span
    of what each subject survives rather than anything read off its current state.
    """
    from types import SimpleNamespace

    from conftest import genesis_store
    from packages.capability.market.wiring import allocation_ceilings

    # world -> agents that must have a ceiling. `sensing` is the control: its agents act for
    # subjects that state no survival range, so they get NO entry — and absent is not zero,
    # because a ceiling of 0.0 would refuse every trade they are in.
    expected = {"simulation": {"fern", "tomato", "succulent"}, "sensing": set()}

    checked = 0
    for world, want in expected.items():
        store = genesis_store(world=world)
        venues = [r["m"] for r in
                  store.query("SELECT ?m WHERE { ?m a market:Market }")["results"]["bindings"]]
        # Aggregated across the world's venues: a plant bids at the barrel, the supplier at the
        # city mains, and only the first kind acts for something with a survival range.
        found: dict[str, float] = {}
        for venue in venues:
            # `allocation_ceilings` reads only the uri; a Market is not needed to ask the store.
            found |= allocation_ceilings(store.query, SimpleNamespace(uri=venue["value"]))
            checked += 1
        assert set(found) == want, f"{world}: ceilings for {sorted(found)}, expected {sorted(want)}"
        assert all(v > 0 for v in found.values()), f"{world}: a ceiling of zero refuses everything"
    assert checked, "no markets found in any world — the fixture stopped building them"

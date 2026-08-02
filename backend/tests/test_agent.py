"""Tests for the deterministic plant agent (no LLM, no infra)."""

import pytest

from agora.agent import Agent, Charter, load_agents, load_charters, value_bid
from agora.auction import propose_match, run_round
from agora.market import Limits, MarketState, Offer


def charter(target=0.55, endowment=100.0, lpf=2.0, maxv=0.80, low=0.35, high=0.65) -> Charter:
    return Charter(
        agent="fern",
        plant_uri="http://example.org/agora#fern",
        species="fern",
        target=target,
        endowment=endowment,
        litres_per_fraction=lpf,
        max_value_per_l=maxv,
        low=low,
        high=high,
    )


# --- the agent judges its own band (not the gateway) -----------------------

def test_agent_computes_its_own_band():
    a = Agent.from_charter(charter(low=0.35, high=0.65))
    assert a.band(0.20) == "LOW"
    assert a.band(0.50) == "OK"
    assert a.band(0.80) == "HIGH"


def test_same_reading_different_verdicts():
    # The same 0.18 is LOW for a fern but OK for a succulent — desire-relative judgment.
    fern = Agent.from_charter(charter(low=0.35, high=0.65))
    succulent = Agent.from_charter(charter(low=0.12, high=0.30))
    assert fern.band(0.18) == "LOW"
    assert succulent.band(0.18) == "OK"


# --- cede reflex -----------------------------------------------------------

def test_cede_at_or_above_target():
    c = charter(target=0.55)
    assert value_bid(0.55, c, balance=100.0) is None
    assert value_bid(0.70, c, balance=100.0) is None


def test_broke_agent_cedes():
    assert value_bid(0.10, charter(), balance=0.0) is None


# --- the value curve -------------------------------------------------------

def test_dry_plant_bids():
    bid = value_bid(0.20, charter(target=0.55), balance=100.0)
    assert bid is not None
    assert bid.agent == "fern"
    assert bid.max_qty_l > 0
    assert bid.max_price_per_l > 0


def test_drier_means_higher_price():
    c = charter(target=0.55)
    drier = value_bid(0.10, c, balance=100.0)
    wetter = value_bid(0.40, c, balance=100.0)
    assert drier.max_price_per_l > wetter.max_price_per_l
    assert drier.max_qty_l > wetter.max_qty_l  # bigger deficit -> more litres


def test_demand_scales_with_litres_per_fraction():
    dry = 0.15
    small_pot = value_bid(dry, charter(lpf=1.0), balance=1000.0)
    big_pot = value_bid(dry, charter(lpf=4.0), balance=1000.0)
    assert big_pot.max_qty_l == pytest.approx(4 * small_pot.max_qty_l)


# --- bids are a function of *unmet* demand ---------------------------------

def test_prior_allocation_reduces_bid():
    c = charter(target=0.55)
    full = value_bid(0.15, c, balance=1000.0, allocated_l=0.0)
    partial = value_bid(0.15, c, balance=1000.0, allocated_l=0.5)
    assert partial.max_qty_l == pytest.approx(full.max_qty_l - 0.5)


def test_satisfied_demand_cedes():
    c = charter(target=0.55)
    full = value_bid(0.15, c, balance=1000.0)
    assert value_bid(0.15, c, balance=1000.0, allocated_l=full.max_qty_l) is None


# --- affordability ---------------------------------------------------------

def test_affordability_caps_quantity():
    c = charter(target=0.55, maxv=0.80)
    # bone dry: big physical demand, but a tiny wallet caps the litres.
    poor = value_bid(0.05, c, balance=0.30)
    rich = value_bid(0.05, c, balance=1000.0)
    assert poor.max_qty_l < rich.max_qty_l
    assert poor.max_qty_l * poor.max_price_per_l <= 0.30 + 1e-6


# --- config loading --------------------------------------------------------

def test_load_agents_from_config():
    agents = load_agents()
    assert {a.charter.agent for a in agents} == {"fern", "tomato", "succulent"}
    fern = next(a for a in agents if a.charter.agent == "fern")
    assert fern.balance == fern.charter.endowment == 100.0


# --- integration: agents -> auction -> clearing ----------------------------

def test_agents_drive_a_full_round():
    agents = load_agents()
    # Dry moisture readings per plant (well below target) -> real bids.
    readings = {"fern": 0.15, "tomato": 0.20, "succulent": 0.05}

    bids = []
    for a in agents:
        b = a.bid(readings[a.charter.agent])
        if b is not None:
            bids.append(b)
    assert bids, "dry plants should bid"

    state = MarketState(
        bids={b.agent: b for b in bids},
        wallets={a.charter.agent: a.balance for a in agents},
        certified=frozenset({"supplier", *(a.charter.agent for a in agents)}),
        limits=Limits(tank_capacity_l=100.0, rot_headroom_l={}),
    )
    offer = Offer(supplier="supplier", quantity_l=2.0, reserve_price_per_l=0.20)

    result = run_round(offer, bids, state, round_id="R-1")
    assert result.validation.ok, result.validation.violations
    assert result.vouchers  # someone got water
    assert result.trade.total_qty_l <= 2.0 + 1e-9  # supply respected


def test_above_target_plant_stays_out_of_the_cluster():
    agents = load_agents()
    # All plants comfortably above target -> nobody bids -> no auction.
    readings = {"fern": 0.90, "tomato": 0.90, "succulent": 0.90}
    bids = [b for a in agents if (b := a.bid(readings[a.charter.agent]))]
    assert bids == []

"""Tests for the host's auction (propose_match) and the host -> clearing round."""

import pytest

from agent.auction import propose_match, run_round
from agent.market import Bid, Limits, MarketState, Offer


def offer(quantity_l=5.0, reserve=0.20) -> Offer:
    return Offer(supplier="supplier", quantity_l=quantity_l, reserve_price_per_l=reserve)


def state(**overrides) -> MarketState:
    base = dict(
        bids={},  # filled per test where solvency matters; propose_match doesn't need it
        wallets={"fern": 100.0, "tomato": 100.0, "succulent": 100.0},
        certified=frozenset({"supplier", "fern", "tomato", "succulent"}),
        limits=Limits(tank_capacity_l=100.0, rot_headroom_l={}),
    )
    base.update(overrides)
    return MarketState(**base)


# --- propose_match ---------------------------------------------------------

def test_below_reserve_excluded():
    bids = [Bid("fern", 3.0, 0.10)]  # below reserve 0.20
    trade = propose_match(offer(), bids)
    assert trade.lines == ()


def test_no_bids_is_no_sale():
    assert propose_match(offer(), []).lines == ()


def test_pays_own_bid_price():
    trade = propose_match(offer(), [Bid("fern", 2.0, 0.45)])
    assert len(trade.lines) == 1
    assert trade.lines[0].price_per_l == 0.45
    assert trade.lines[0].qty_l == 2.0


def test_highest_price_filled_first_under_scarcity():
    # 5 L supply; demand is 4 + 4 = 8; tomato (0.55) outranks fern (0.40).
    bids = [Bid("fern", 4.0, 0.40), Bid("tomato", 4.0, 0.55)]
    trade = propose_match(offer(quantity_l=5.0), bids)
    by_agent = {l.agent: l for l in trade.lines}
    assert by_agent["tomato"].qty_l == 4.0   # full
    assert by_agent["fern"].qty_l == 1.0     # partial: only 1 L left
    assert trade.total_qty_l == 5.0


def test_deterministic_tie_break_by_agent():
    # Equal price, supply only covers one fully -> lexicographically smaller agent first.
    bids = [Bid("tomato", 3.0, 0.40), Bid("fern", 3.0, 0.40)]
    trade = propose_match(offer(quantity_l=3.0), bids)
    # fern wins the tie and consumes all supply; tomato gets no line.
    assert len(trade.lines) == 1
    assert trade.lines[0].agent == "fern"
    assert trade.lines[0].qty_l == 3.0


def test_full_demand_when_supply_ample():
    bids = [Bid("fern", 2.0, 0.40), Bid("tomato", 1.0, 0.50)]
    trade = propose_match(offer(quantity_l=10.0), bids)
    assert trade.total_qty_l == 3.0  # everyone filled


# --- run_round (host -> clearing) ------------------------------------------

def test_round_happy_path_issues_grants():
    bids = [Bid("tomato", 4.0, 0.55), Bid("fern", 4.0, 0.40)]
    st = state(bids={b.agent: b for b in bids})
    result = run_round(offer(quantity_l=5.0), bids, st, round_id="R-1")
    assert result.validation.ok, result.validation.violations
    assert {g.sub for g in result.vouchers} == {"tomato", "fern"}
    assert result.trade.total_qty_l == 5.0
    tomato = next(g for g in result.vouchers if g.sub == "tomato")
    assert tomato.debit == pytest.approx(4.0 * 0.55)


def test_round_red_light_on_constitution():
    # Host greedily proposes 4 L to tomato, but tomato's rot headroom is 1 L -> clearing rejects.
    bids = [Bid("tomato", 4.0, 0.55)]
    st = state(
        bids={b.agent: b for b in bids},
        limits=Limits(tank_capacity_l=100.0, rot_headroom_l={"tomato": 1.0}),
    )
    result = run_round(offer(quantity_l=5.0), bids, st, round_id="R-1")
    assert not result.validation.ok
    assert result.vouchers == []
    assert any("rot headroom" in v for v in result.validation.violations)


def test_round_red_light_on_insolvency():
    bids = [Bid("fern", 3.0, 0.50)]
    st = state(bids={b.agent: b for b in bids}, wallets={"fern": 0.50})  # cost 1.50 > 0.50
    result = run_round(offer(quantity_l=5.0), bids, st, round_id="R-1")
    assert not result.validation.ok
    assert result.vouchers == []
    assert any("exceeds wallet" in v for v in result.validation.violations)

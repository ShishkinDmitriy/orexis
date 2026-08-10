"""The allocation rule, and the host -> clearing path that runs whichever rule is in force.

`propose_match` moved into `capabilities/matching/` when the format became a capability (#66),
so it is exercised here through the module that provides it — the same object `hosting.py` gets
from `agent.provider`. `run_round` stayed in `agent/auction.py`, because propose-validate-issue
is true of every rule, and it now takes the matcher rather than importing one.
"""

import pytest

from agent.auction import run_round
from agent.capabilities.matching.module import PayAsBidModule, UniformPriceModule
from agent.market import Bid, Limits, MarketState, Offer

# The rule under test. It is static because a lot and a set of bids fully determine the answer —
# which is what lets it be checked without a world, and a format be swapped without the host
# knowing. `hosting.py` reaches this same function through `agent.provider`.
propose_match = PayAsBidModule.propose_match


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
    result = run_round(offer(quantity_l=5.0), bids, st, round_id="R-1", match=propose_match)
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
    result = run_round(offer(quantity_l=5.0), bids, st, round_id="R-1", match=propose_match)
    assert not result.validation.ok
    assert result.vouchers == []
    assert any("rot headroom" in v for v in result.validation.violations)


def test_round_red_light_on_insolvency():
    bids = [Bid("fern", 3.0, 0.50)]
    st = state(bids={b.agent: b for b in bids}, wallets={"fern": 0.50})  # cost 1.50 > 0.50
    result = run_round(offer(quantity_l=5.0), bids, st, round_id="R-1", match=propose_match)
    assert not result.validation.ok
    assert result.vouchers == []
    assert any("exceeds wallet" in v for v in result.validation.violations)


# --- uniform price ---------------------------------------------------------
#
# The second member of the family, and the reason it exists: the same allocation as pay-as-bid,
# a different bill. Reached the same way `hosting.py` reaches it — off the module that provides
# it — so these check the object a host would actually be handed.

uniform_price = UniformPriceModule.propose_match


def test_uniform_price_allocates_exactly_as_pay_as_bid():
    """The rules differ about the bill, not about who gets what.

    Worth pinning: the two walk the same demand curve and the walk is written out twice, so
    nothing but a test stops them drifting apart where they are meant to agree.
    """
    bids = [Bid("fern", 4.0, 0.40), Bid("tomato", 4.0, 0.55)]
    discriminatory = propose_match(offer(quantity_l=5.0), bids)
    uniform = uniform_price(offer(quantity_l=5.0), bids)
    assert ({(l.agent, l.qty_l) for l in uniform.lines}
            == {(l.agent, l.qty_l) for l in discriminatory.lines})


def test_every_winner_pays_the_lowest_accepted_bid():
    # 5 L supply; tomato (0.55) fills 4, fern (0.40) fills the last 1 and is marginal.
    bids = [Bid("fern", 4.0, 0.40), Bid("tomato", 4.0, 0.55)]
    trade = uniform_price(offer(quantity_l=5.0), bids)
    assert {l.price_per_l for l in trade.lines} == {0.40}
    # And that is the whole difference from pay-as-bid, which charges tomato its own 0.55.
    assert {l.price_per_l for l in propose_match(offer(quantity_l=5.0), bids).lines} == {0.40, 0.55}


def test_an_uncontested_round_clears_at_the_reserve():
    """#50, dissolved rather than branched.

    Combined demand of 3 L against a 10 L lot: nothing was scarce, nobody had a rival, and the
    demand curve never crossed supply — so the clearing price is where it started, the reserve.
    No contested-or-not test computes this; it is what the walk leaves behind.
    """
    bids = [Bid("fern", 2.0, 0.40), Bid("tomato", 1.0, 0.50)]
    trade = uniform_price(offer(quantity_l=10.0, reserve=0.20), bids)
    assert trade.total_qty_l == 3.0                       # everyone filled
    assert {l.price_per_l for l in trade.lines} == {0.20}  # everyone pays the reserve
    # Under pay-as-bid the same round charges each its own urgency — the defect #50 records.
    assert {l.price_per_l for l in propose_match(offer(quantity_l=10.0), bids).lines} == {0.40, 0.50}


def test_a_contested_round_does_not_fall_to_the_reserve():
    """The other half of #50's warning: this must not become a way to pay less by bidding late."""
    bids = [Bid("fern", 4.0, 0.40), Bid("tomato", 4.0, 0.55)]
    trade = uniform_price(offer(quantity_l=5.0, reserve=0.20), bids)
    assert {l.price_per_l for l in trade.lines} == {0.40}  # the margin, not the floor


def test_uniform_price_still_excludes_below_reserve():
    assert uniform_price(offer(), [Bid("fern", 3.0, 0.10)]).lines == ()


def test_uniform_price_no_bids_is_no_sale():
    assert uniform_price(offer(), []).lines == ()


def test_a_lot_exhausted_exactly_prices_at_the_last_bid_filled():
    """The one case where lowest-accepted and highest-rejected could differ.

    Demand meets supply exactly on fern's bid, so nothing is partially filled and nothing is
    rejected. The price is the lowest bid that WAS accepted — 0.40, not the reserve, because the
    curve did cross supply, and not tomato's 0.55, because fern's units cleared too.
    """
    bids = [Bid("fern", 2.0, 0.40), Bid("tomato", 3.0, 0.55)]
    trade = uniform_price(offer(quantity_l=5.0, reserve=0.20), bids)
    assert trade.total_qty_l == 5.0
    assert {l.price_per_l for l in trade.lines} == {0.40}


def test_a_round_run_under_uniform_price_clears_and_issues():
    """End to end through the path every rule shares — `run_round` takes the matcher."""
    bids = [Bid("tomato", 4.0, 0.55), Bid("fern", 4.0, 0.40)]
    st = state(bids={b.agent: b for b in bids})
    result = run_round(offer(quantity_l=5.0), bids, st, round_id="R-1", match=uniform_price)
    assert result.validation.ok, result.validation.violations
    tomato = next(g for g in result.vouchers if g.sub == "tomato")
    assert tomato.debit == pytest.approx(4.0 * 0.40)  # billed at the clearing price, not its bid

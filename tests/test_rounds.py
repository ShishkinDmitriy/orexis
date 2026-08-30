"""A round is a fact, on both sides (#357).

knowledge/decisions/a-round-is-a-fact-and-offering-is-an-action.md, step 1. An open round
used to be a dict on the host and `pending` on the bidder; it is a `market:Round` in each
agent's own graph now, written on announce or on offer, retracted when it is over for that
agent, and swept once past its close. What it must never carry is the host's window and
cooldown — the private beliefs that keep a bidder from timing its arrival.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orexis_capability_market import rounds
from orexis_capability_market.terms import NS as MARKET
BID_WINDOW_S, ROUND_COOLDOWN_S = MARKET + "bidWindowS", MARKET + "roundCooldownS"

from conftest import build_agent, genesis_store, wired_markets


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


def market_of(agent):
    return wired_markets(agent)[0]


def _row_terms(agent, uri):
    from orexis_modality_graph.store import bindings
    return {r["p"] for r in bindings(agent.beliefs.query(
        f"SELECT ?p WHERE {{ GRAPH ?g {{ <{uri}> ?p ?o }} }}"))}


# --- the host --------------------------------------------------------------------------------


def test_the_host_holds_the_round_it_announced_and_lets_it_go_at_close(make):
    host = make("supplier")
    host.deliver("sensors/barrel1_level/reading", {"value": 3.0})
    assert rounds.rounds_of(host) == []
    host.deliver("readings/fern", {"agent": "fern", "band": "LOW",
                                   "property": "http://example.org/orexis/water#SoilMoisture"})
    held = rounds.rounds_of(host)
    assert len(held) == 1, "one round announced, one row held"
    rnd = held[0]
    assert rnd.venue.endswith("barrel1"), "the downstream venue, not the one I buy in"
    assert rnd.lot_l == pytest.approx(min(host.hosting().beliefs.quantity_l, 3.0))
    assert rnd.reserve_per_l == pytest.approx(host.hosting().beliefs.reserve_price_per_l)
    assert rnd.is_open(), "closes in the future, by the announced window"
    assert rnd.auction_id == host.hosting().open_auction["auction_id"]

    host.hosting().close()
    assert rounds.rounds_of(host) == [], "over — retracted, whatever the bids said"


def test_the_row_never_carries_the_hosts_private_clocks(make):
    """`bidWindowS` and `roundCooldownS` are private so a bidder cannot time its arrival;
    `closesAt` is what the offer already says. Scanned on the row, not trusted."""
    host = make("supplier")
    host.deliver("sensors/barrel1_level/reading", {"value": 3.0})
    host.deliver("readings/fern", {"agent": "fern", "band": "LOW",
                                   "property": "http://example.org/orexis/water#SoilMoisture"})
    (rnd,) = rounds.rounds_of(host)
    terms = _row_terms(host, rnd.uri)
    assert terms, "the row has triples — the scan found it"
    assert BID_WINDOW_S not in terms and ROUND_COOLDOWN_S not in terms
    assert not any(t.endswith(("bidWindowS", "roundCooldownS")) for t in terms)


# --- the bidder ------------------------------------------------------------------------------


def test_the_bidder_holds_the_round_it_was_told_and_lets_it_go_on_the_claim(make):
    fern = make("fern", genesis_store({"fern": 0.10}))
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "quantity_l": 2.0,
                                      "reserve_price_per_l": 0.4, "closes_in_s": 30})
    (rnd,) = rounds.rounds_of(fern)
    assert (rnd.venue, rnd.auction_id, rnd.lot_l, rnd.reserve_per_l) == (market.uri, "r1", 2.0, 0.4)
    assert rnd.is_open()
    assert 25 < (rnd.closes_at - datetime.now(timezone.utc)).total_seconds() <= 30

    fern.deliver(f"{market.claim_topic}/fern",
                 {"auction_id": "r1", "jti": "j1", "sub": "fern", "amount_l": 0.5, "debit": 0.2})
    assert rounds.rounds_of(fern) == [], "won — the round is over for me"


def test_a_round_the_bidder_was_never_told_ended_is_swept_once_past_its_close(make):
    """A bidder that lost hears nothing. The clock ends the row, and the sweep runs on the one
    event that always comes — the next offer."""
    fern = make("fern", genesis_store({"fern": 0.10}))
    market = market_of(fern)
    rounds.open_round(fern, market.uri, "old", 2.0, 0.4,
                      datetime.now(timezone.utc) - timedelta(seconds=5))
    assert len(rounds.rounds_of(fern)) == 1 and not rounds.rounds_of(fern)[0].is_open()
    fern.deliver(market.offer_topic, {"auction_id": "r2", "quantity_l": 2.0,
                                      "reserve_price_per_l": 0.4, "closes_in_s": 30})
    ids = {r.auction_id for r in rounds.rounds_of(fern)}
    assert ids == {"r2"}, "the expired row went, the new one stands"


def test_a_round_that_closed_before_the_look_came_back_is_let_go(make):
    fern = make("fern")   # no reading: it waits for a look, and the auction closes first
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r3", "quantity_l": 2.0,
                                      "reserve_price_per_l": 0.4, "closes_in_s": 30})
    assert len(rounds.rounds_of(fern)) == 1
    fern.bidding().give_up()
    assert rounds.rounds_of(fern) == []


def test_the_housekeeping_clock_retracts_what_the_round_clock_ended(make):
    """A bidder is never told a round closed, so the row goes by its own `closesAt` — and what
    GUARANTEES it goes is the agent's own housekeeping tick, not an offer it may stop receiving
    (#398). An agent that stops bidding used to keep every row it had last heard: invisible to
    every read, because `is_open` filters, and visible on the one line that watches for exactly
    this — a belief base that grows with what an agent has done.
    """
    fern = make("fern")
    market = market_of(fern)

    #  Measured with nothing else in flight: an agent that has just been told an offer holds a
    #  ledger row too, and this is about the ROUND rows.
    held = len(fern.beliefs)
    rounds.open_round(fern, market.uri, "r10", 2.0, 0.4,
                      datetime.now(timezone.utc) - timedelta(seconds=1))
    assert rounds.rounds_of(fern), "held, though already closed — nothing has swept yet"
    assert len(fern.beliefs) > held, "the round is a fact, and facts are held"

    gone = fern.upkeep.sweep()
    assert gone == 1
    assert rounds.rounds_of(fern) == []
    assert len(fern.beliefs) == held, "and the belief base is where it started"


# --- the sovereign can ask ---------------------------------------------------------------------


def test_the_fact_is_in_the_belief_modality_where_the_sovereign_asks(make):
    """`orexis-ask <world> fern beliefs 'SELECT …'` reads the belief store; the round is
    there as an ordinary fact, keyed by the venue the T-Box already names."""
    from orexis_modality_graph.store import bindings

    fern = make("fern", genesis_store({"fern": 0.10}))
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r4", "quantity_l": 1.5,
                                      "reserve_price_per_l": 0.3, "closes_in_s": 30})
    rows = bindings(fern.beliefs.query_union(
        "SELECT ?lot WHERE { ?venue market:hasRound ?r . ?r market:lotL ?lot ; "
        "market:closesAt ?t FILTER(?t > NOW()) }"))
    assert [float(r["lot"]) for r in rows] == [1.5]

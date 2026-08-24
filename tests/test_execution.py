"""Execution: plan, commit the head as an intention, hand it to its actor — one road.

knowledge/decisions/an-intention-is-a-plan-committed-to.md. What these pin is the seam and
not the search: an intention carries the lever the plan chose, every trigger goes through the
same three phases, a standing step is taken without a second search, and a row is linked to
the code that takes it by a triple rather than by a dispatch table.
"""

from __future__ import annotations

import rdflib

from agent import execution, loader, menu
from agent.planner import Planner

from conftest import MOISTURE, build_agent, genesis_store

ACQUIRE = "http://example.org/orexis#Acquire"
OBSERVE = "http://example.org/orexis#Observe"
ACTUATE = "http://example.org/orexis#Actuate"
APPLY = "http://example.org/orexis#Apply"
OFFER = "http://example.org/orexis#Offer"
TAKEN_BY = rdflib.URIRef("http://example.org/orexis#takenBy")


def keeper_of(agent):
    return next(m for m in agent.modules if m.name == "intention")


def stake_of(agent, prop=MOISTURE):
    return next(d for d in agent.pursuing()
                if not d.is_duty and not d.is_epistemic and d.observed_property == prop)


# --- an intention is the plan's head, lever included ------------------------------------------


def test_the_tick_commits_every_move_and_not_only_the_look(monkeypatch):
    """The keeper's tick used to carry out Observe alone and drop an Acquire on the floor. A
    thirsty fern with a fresh reading now has an Acquire STANDING after one tick — committed
    through the venue the plan chose — and it stands because no round is open to bid in."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.deliberate_on_gaps()
    acquires = keeper.standing(means=ACQUIRE, observed_property=MOISTURE)
    assert len(acquires) == 1, "the plan's head is committed, whoever will carry it out"
    assert acquires[0].via == fern.me.markets[0].uri, "and the ledger says THROUGH which venue"
    assert fern.sent.to(f"{fern.me.markets[0].bid_topic}/fern") == [], \
        "nothing to bid in yet — the actor said 'not now' and the intention stands"


def test_a_round_is_answered_from_what_stands_without_a_second_search(monkeypatch):
    """The amortisation, finally for Acquire: an offer arriving while the commitment stands is
    executed — look, then bid — and the search does not run again."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    keeper_of(fern).deliberate_on_gaps()
    assert keeper_of(fern).standing(means=ACQUIRE)
    passes = []
    monkeypatch.setattr(Planner, "plan", lambda self, desire: passes.append(desire) or None)
    market = fern.me.markets[0]
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 1, "the standing Acquire is taken"
    assert passes == [], "and nothing was re-decided on the way"


def test_a_round_with_nothing_standing_plans_once_and_commits(monkeypatch):
    """The other order: the market knocks before the tick. One search, one intention, one bid
    — and the intention it leaves behind is the same row the tick would have written."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    market = fern.me.markets[0]
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 1
    standing = keeper_of(fern).standing(means=ACQUIRE, observed_property=MOISTURE)
    assert len(standing) == 1 and standing[0].via == market.uri


def test_the_bidder_holds_no_opinion_of_its_own(monkeypatch):
    """Silence the plan door alone and a thirsty bidder with a reading in hand bids nothing:
    `submit` no longer decides, it executes what the search committed to."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    monkeypatch.setattr(fern.deliberator, "decide", lambda desire: None)
    market = fern.me.markets[0]
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.to(f"{market.bid_topic}/fern") == []
    assert keeper_of(fern).standing(means=ACQUIRE) == []


# --- the link from a row to its code is a triple ---------------------------------------------


def _project():
    g = rdflib.Graph()
    for ttl in loader.ontology_files():
        g.parse(ttl)
    return g


def test_every_means_a_shipped_world_offers_is_taken_by_a_loaded_capability(monkeypatch):
    """A row shipped with no `ag:takenBy` is an intention nothing can carry out. Every means
    on any shipped agent's menu names a family, and every agent holding such a row composes a
    module in that family — which is the whole of 'every affordance is linked to code'."""
    project = _project()
    takers = {str(s): str(o) for s, _, o in project.triples((None, TAKEN_BY, None))}
    assert takers, "no ag:takenBy anywhere — the ontologies stopped stating it"
    rows_seen = 0
    for world, agent_id in (("simulation", "fern"), ("simulation", "supplier"),
                            ("loner", "gardener")):
        monkeypatch.setenv("OREXIS_WORLD", world)
        agent = build_agent(agent_id, genesis_store(world=world), monkeypatch)
        for row in menu.menu_of(agent.beliefs.query, agent.me.uri, agent.desires.query_union):
            rows_seen += 1
            assert row.means in takers, f"{world}/{agent_id}: {row.means} has no ag:takenBy"
            family = execution.taken_by(agent.beliefs.query, row.means)
            assert family == takers[row.means]
            assert agent.providers(family), \
                f"{world}/{agent_id}: {row.means} is taken by {family}, which it does not compose"
    assert rows_seen >= 4
    assert OFFER not in takers, "Offer is on no menu and states no taker, on purpose"


def test_execution_dispatches_by_the_triple_and_never_by_name(monkeypatch):
    """The row goes to whoever the T-Box says, and to every member of the family."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    handed = []
    for m in fern.modules:
        if m.CAPABILITY:
            monkeypatch.setattr(m, "take", lambda row, desire, i, m=m: handed.append(m.name) or False)
    stake = stake_of(fern)
    row = menu.Affordance(means=OBSERVE, observed_property=MOISTURE, via="urn:probe")
    assert execution.carry_out(fern, row, stake, "urn:intent") is False
    assert handed == ["subscribing"], "Observe went to sensing and to nothing else"
    handed.clear()
    row = menu.Affordance(means=ACQUIRE, observed_property=MOISTURE, via="urn:venue")
    execution.carry_out(fern, row, stake, "urn:intent")
    assert handed == ["bidding"]


def test_a_means_nobody_takes_is_logged_and_takes_nothing(monkeypatch, caplog):
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    row = menu.Affordance(means="http://example.org/nowhere#Untaken",
                          observed_property=MOISTURE, via="urn:x")
    with caplog.at_level("ERROR", logger="execution"):
        assert execution.carry_out(fern, row, stake_of(fern), "urn:i") is False
    assert any("nothing takes" in r.message for r in caplog.records)


# --- the patience is one rule for every means -------------------------------------------------


def test_an_impulse_within_patience_writes_no_row(monkeypatch):
    """Two ticks, one intention — and not one standing and one dropped, because the patience is
    asked before anything is adopted."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.deliberate_on_gaps()
    n = len(keeper.standing())
    keeper.deliberate_on_gaps()
    assert len(keeper.standing()) == n
    from agent.store import bindings
    everything = bindings(keeper.agent.intentions.query(
        "SELECT (COUNT(?i) AS ?n) WHERE { GRAPH ?g { ?i a <http://example.org/orexis#Intention> } }"))
    assert int(everything[0]["n"]) == n, "no dropped rows either"

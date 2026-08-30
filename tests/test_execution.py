"""Execution: plan, commit the head as an intention, hand it to its actor — one road.

knowledge/decisions/an-intention-is-a-plan-committed-to.md. What these pin is the seam and
not the search: an intention carries the lever the plan chose, every trigger goes through the
same three phases, a standing step is taken without a second search, and a row is linked to
the code that takes it by a triple rather than by a dispatch table.
"""

from __future__ import annotations

import rdflib

from orexis_agent_progression.act import Act
from orexis_agent_progression import execution
from orexis_agent_deliberation import afforder, pursuit
from assembly import loader
from orexis_agent_deliberation.planner import Planner

from orexis_agent_progression.ontology import beliefs_graph

from conftest import MOISTURE, build_agent, genesis_store, open_round_for, wired_markets

ACQUIRING = "http://example.org/orexis/market#Acquiring"
OBSERVING = "http://example.org/orexis/sensing#Observing"
DOSING = "http://example.org/orexis/actuation#Dosing"
SERVING = "http://example.org/orexis/market#Serving"
OFFERING = "http://example.org/orexis/market#Offering"
TAKEN_BY = rdflib.URIRef("http://example.org/orexis#takenBy")


def keeper_of(agent):
    return next(m for m in agent.modules if m.name == "intention")


def stake_of(agent, prop=MOISTURE):
    return next(d for d in agent.pursuing()
                if not d.is_obligation and not d.is_epistemic
                and getattr(d, "observed_property", None) == prop)


# --- an intention is the plan's head, lever included ------------------------------------------


def test_no_round_open_means_no_acquire_committed_and_the_trace_says_why(monkeypatch):
    """Since #358 the buying row exists only while a round is open. A thirsty fern with no
    round to bid in commits NOTHING on the tick — the want stays hot, the trace shows the
    look weighed and no Acquire on the menu at all, and nothing stands waiting for the market
    to knock."""
    from orexis_agent_progression.store import bindings

    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.agent.deliberator.deliberate_on_gaps()
    assert keeper.standing(action=ACQUIRING) == [], "nothing to bid in, nothing committed"
    assert fern.sent.to(f"{wired_markets(fern)[0].bid_topic}/fern") == []
    weighed = {r["m"] for r in bindings(fern.beliefs.query_union(
        "SELECT DISTINCT ?m WHERE { ?c ag:wouldTake ?m }"))}
    assert OBSERVING in weighed and ACQUIRING not in weighed, \
        "the look was weighed; buying was not on the menu, not merely refused"


def test_the_tick_bids_when_a_round_is_open(monkeypatch):
    """And with a round open the tick commits the Acquire THROUGH the venue and the actor bids
    at once — the row's precondition holds, so the intention is executable when written."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    open_round_for(fern, "fern")
    keeper = keeper_of(fern)
    keeper.agent.deliberator.deliberate_on_gaps()
    acquires = keeper.standing(action=ACQUIRING, want=stake_of(fern).uri)
    assert len(acquires) == 1 and acquires[0].via == wired_markets(fern)[0].uri
    assert len(fern.sent.to(f"{wired_markets(fern)[0].bid_topic}/fern")) == 1


def test_a_round_is_decided_once_and_a_second_impulse_is_absorbed(monkeypatch):
    """One search per round: the offer plans and bids, and the tick that follows finds the
    Acquire standing and searches nothing again."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    market = wired_markets(fern)[0]
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 1
    assert keeper_of(fern).standing(action=ACQUIRING)
    from orexis_agent_deliberation.planner import NOT_BETTER, Plan

    passes = []
    monkeypatch.setattr(Planner, "plan",
                        lambda self, desire: passes.append(desire) or Plan(NOT_BETTER))
    fern.deliberator.deliberate_on_gaps()
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 1, "no second bid"
    #  The freshness want is met and the stake stands, so the tick has nothing to search
    #  FOR; the one pass it may run is the stake's, which `adopt` then absorbs.
    assert not [d for d in passes if not d.is_epistemic] or \
        len(keeper_of(fern).standing(action=ACQUIRING)) == 1


def test_a_round_with_nothing_standing_plans_once_and_commits(monkeypatch):
    """The other order: the market knocks before the tick. One search, one intention, one bid
    — and the intention it leaves behind is the same row the tick would have written."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    market = wired_markets(fern)[0]
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 1
    standing = keeper_of(fern).standing(action=ACQUIRING, want=stake_of(fern).uri)
    assert len(standing) == 1 and standing[0].via == market.uri


def test_the_bidder_holds_no_opinion_of_its_own(monkeypatch):
    """Silence the plan door alone and a thirsty bidder with a reading in hand bids nothing:
    `submit` no longer decides, it executes what the search committed to."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    monkeypatch.setattr(fern.deliberator, "decide", lambda desire: None)
    market = wired_markets(fern)[0]
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert fern.sent.to(f"{market.bid_topic}/fern") == []
    assert keeper_of(fern).standing(action=ACQUIRING) == []


# --- the link from a row to its code is a triple ---------------------------------------------


def _actions():
    g = rdflib.Graph()
    for ttl in loader.action_files():
        g.parse(ttl)
    return g


def test_every_means_a_shipped_world_offers_is_taken_by_a_loaded_capability(monkeypatch):
    """An action with no `ag:takenBy` is an intention nothing can carry out. Every means on any
    shipped agent's menu comes from an action naming a family, and every agent holding such a
    row composes a module in that family — which is the whole of 'every affordance is linked
    to code'."""
    actions = _actions()
    takers = {str(a): str(f) for a, f in actions.subject_objects(TAKEN_BY)}
    assert takers, "no ag:takenBy anywhere — the action files stopped stating it"
    rows_seen = 0
    for world, agent_id in (("simulation", "fern"), ("simulation", "supplier"),
                            ("loner", "gardener")):
        monkeypatch.setenv("OREXIS_WORLD", world)
        agent = build_agent(agent_id, genesis_store(world=world), monkeypatch)
        open_round_for(agent, agent_id)
        for row in afforder.affordances_of(agent.beliefs.query, agent.me.uri, agent.desires.query_union,
                                beliefs_graph(agent.id)):
            rows_seen += 1
            assert row.action in takers, f"{world}/{agent_id}: {row.action} has no ag:takenBy"
            family = execution.taken_by(agent.beliefs.query, row.action)
            assert family == takers[row.action]
            assert agent.providers(family), \
                f"{world}/{agent_id}: {row.action} is taken by {family}, which it does not compose"
    assert rows_seen >= 4
    assert takers[OFFERING].endswith("Hosting"), "Offer is an action since #359, taken by the host"


def test_execution_dispatches_by_the_triple_and_never_by_name(monkeypatch):
    """The row goes to whoever the T-Box says, and to every member of the family."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    handed = []
    for m in fern.modules:
        if m.CAPABILITY:
            monkeypatch.setattr(m, "take", lambda row, desire, i, m=m: handed.append(m.name) or False)
    stake = stake_of(fern)
    row = afforder.Affordance(action=OBSERVING, want=stake.uri, about=MOISTURE, via="urn:probe")
    assert execution.carry_out(fern, Act.from_row(row), stake, "urn:intent") is False
    assert handed == ["subscribing"], "Observe went to sensing and to nothing else"
    handed.clear()
    row = afforder.Affordance(action=ACQUIRING, want=stake.uri, about=MOISTURE, via="urn:venue")
    execution.carry_out(fern, Act.from_row(row), stake, "urn:intent")
    assert handed == ["bidding"]


def test_a_means_nobody_takes_is_logged_and_takes_nothing(monkeypatch, caplog):
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    row = afforder.Affordance(action="http://example.org/nowhere#Untaken",
                          want=stake_of(fern).uri, about=MOISTURE, via="urn:x")
    with caplog.at_level("ERROR", logger="execution"):
        assert execution.carry_out(fern, Act.from_row(row), stake_of(fern), "urn:i") is False
    assert any("nothing takes" in r.message for r in caplog.records)


# --- the patience is one rule for every means -------------------------------------------------


def test_an_impulse_within_patience_writes_no_row(monkeypatch):
    """Two ticks, one intention — and not one standing and one dropped, because the patience is
    asked before anything is adopted."""
    fern = build_agent("fern", genesis_store({"fern": 0.10}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.agent.deliberator.deliberate_on_gaps()
    n = len(keeper.standing())
    keeper.agent.deliberator.deliberate_on_gaps()
    assert len(keeper.standing()) == n
    from orexis_agent_progression.store import bindings
    everything = bindings(keeper.agent.intentions.query(
        "SELECT (COUNT(?i) AS ?n) WHERE { GRAPH ?g { ?i a <http://example.org/orexis#Intention> } }"))
    assert int(everything[0]["n"]) == n, "no dropped rows either"

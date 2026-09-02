"""An action may turn out more than one way, and the odds enter the search as expected
cost (#522). Losing a round is what the other bidders did, so a venue's odds are a
first-order belief — two counts the bidder keeps — read banded by Acquiring's `Allocated`
outcome; a bid at half odds costs twice its price in attempts; the step relies on one
outcome and the world is held to it. No branch in the plan, and no chance for the pump."""
from __future__ import annotations

import pytest

from orexis_agent_deliberation import effects
from orexis_agent_deliberation.planner import Planner
from orexis_capability_actuation.terms import DOSING
from orexis_capability_market import rounds
from orexis_capability_market.terms import ACQUIRING, ALLOCATED, NOT_ALLOCATED
from orexis_agent_progression.store import bindings
from conftest import MOISTURE, build_agent, genesis_store, open_round_for, stake_of, wired_markets


@pytest.fixture
def fern(monkeypatch):
    monkeypatch.setenv("OREXIS_WORLD", "simulation")
    agent = build_agent("fern", genesis_store({("fern", MOISTURE): 0.30}), monkeypatch)
    open_round_for(agent, "fern")
    return agent


def _desire(agent):
    return next(g for g in agent.pursuing()
                if getattr(g, "observed_property", None) == MOISTURE and not g.is_epistemic)


def _pose_odds(agent, entered: int, won: int):
    venue = wired_markets(agent)[0].uri
    for _ in range(entered):
        rounds.tally(agent, venue, won=False)
    for _ in range(won):
        rounds.tally(agent, venue, won=True)
    return venue


def test_an_action_states_its_ways_of_turning_out_or_just_one(fern):
    ways = effects.outcomes_of(fern.beliefs, ACQUIRING)
    assert [w.get("outcome") for w in ways] == [ALLOCATED, NOT_ALLOCATED]
    assert all(w.get("likelihood") for w in ways), "each way says how likely it is"
    dosing = effects.outcomes_of(fern.beliefs, DOSING)
    assert len(dosing) == 1 and dosing[0].get("outcome") is None and dosing[0].get("construct"), \
        "an action stating no outcome has exactly one, itself"


def test_the_odds_are_banded_first_order_counts_with_an_even_prior(fern):
    venue = _pose_odds(fern, 0, 0)
    bind = dict(me=fern.me.uri, via=venue, beliefs=f"http://example.org/orexis/graph/beliefs/{fern.id}")
    allocated = effects.rule_for(fern.beliefs, ACQUIRING, ALLOCATED)
    assert effects.likelihood_of(fern.beliefs, allocated, **bind) == pytest.approx(0.5), "no history: even"
    _pose_odds(fern, 4, 3)                              # (3+1)/(4+2) = 0.67 -> the 0.75 band
    assert effects.likelihood_of(fern.beliefs, allocated, **bind) == pytest.approx(0.75)
    not_allocated = effects.rule_for(fern.beliefs, ACQUIRING, NOT_ALLOCATED)
    assert effects.likelihood_of(fern.beliefs, not_allocated, **bind) == pytest.approx(0.25)
    _pose_odds(fern, 10, 0)                             # 14 entered, 3 won: (3+1)/(14+2) = 0.25
    assert effects.likelihood_of(fern.beliefs, allocated, **bind) == pytest.approx(0.25)
    _pose_odds(fern, 30, 0)                             # 44 entered, 3 won: below the last band — the floor, never zero
    assert effects.likelihood_of(fern.beliefs, allocated, **bind) == pytest.approx(0.125)


def test_the_way_not_relied_on_nets_to_nothing(fern):
    venue = wired_markets(fern)[0].uri
    added, retracted = effects.apply(fern.beliefs, ACQUIRING, outcome=NOT_ALLOCATED,
                                     me=fern.me.uri, via=venue, subject=fern.me.acts_for,
                                     about=MOISTURE, litres="0.5",
                                     beliefs=f"http://example.org/orexis/graph/beliefs/{fern.id}")
    assert added == [] and retracted == []


def test_poor_odds_make_the_same_plan_dearer_and_the_step_relies_on_the_allocation(fern):
    even = Planner(fern, fern.me).plan(_desire(fern))
    assert [s.action for s in even.steps] == [ACQUIRING] and even.cost is not None
    assert even.steps[0].relies_on == ALLOCATED, "the plan counts on the round clearing to me"
    _pose_odds(fern, 10, 0)                             # a venue that never allocates
    poor = Planner(fern, fern.me).plan(_desire(fern))
    assert [s.action for s in poor.steps] == [ACQUIRING], "still the only lever, so still taken"
    assert poor.cost == pytest.approx(even.cost * 4), "at the floor odds it costs four times as much in attempts"


def test_the_ledger_step_names_the_outcome_it_relies_on(fern):
    from orexis_agent_deliberation import pursuit
    uri = pursuit.pursue(fern, _desire(fern))
    rows = bindings(fern.intentions.query_union(f"""
SELECT ?o WHERE {{ <{uri}> orexis:by ?s . ?s orexis:reliesOn ?o }}"""))
    assert [r["o"] for r in rows] == [ALLOCATED]
    assert fern.keeper.standing(want=stake_of(fern).uri)[0].step.relies_on == ALLOCATED


def test_the_bidder_counts_what_the_venue_did(fern):
    market = wired_markets(fern)[0]
    assert rounds.tallies(fern, market.uri) == (0, 0)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert rounds.tallies(fern, market.uri) == (1, 0), "a bid went out: a round entered"
    fern.deliver(f"{market.claim_topic}/fern", {"auction_id": "r1", "amount_l": 0.5, "debit": 0.2})
    assert rounds.tallies(fern, market.uri) == (1, 1), "and the claim came back: won"

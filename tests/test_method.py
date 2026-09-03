"""A method is the steps an action comes to (#523). Acquiring is the decision the search
chooses; what taking it comes to is two steps the keeper walks on feedback — tender, then
present — each declaring what it waits for. The protocol that was a chain of reactions in the
bidder's Python is a plan the ledger shows, and losing a round is a step lapsing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_progression.act import method_of, takers_of
from orexis_agent_progression.store import bindings
from orexis_capability_market.terms import ACQUIRING, PRESENTING, TENDERING
from conftest import MOISTURE, build_agent, genesis_store, predicted_reading, stake_of


def _fern(monkeypatch, moisture=0.30):
    return build_agent("fern", genesis_store({"fern": moisture}), monkeypatch)


def test_the_method_is_read_in_order_and_the_takers_follow_it(monkeypatch):
    fern = _fern(monkeypatch)
    assert method_of(fern.beliefs.query, ACQUIRING) == [TENDERING, PRESENTING]
    assert method_of(fern.beliefs.query, TENDERING) == [], "a step of a method is its own one step"
    assert [m.name for m in takers_of(fern, ACQUIRING)] == ["bidding"], \
        "an abstract action is taken through its steps, so its taker is theirs"


def test_adopting_an_action_with_a_method_expands_it_and_the_last_step_inherits_the_end(monkeypatch):
    fern = _fern(monkeypatch)
    keeper, want = fern.keeper, stake_of(fern).uri
    from orexis_agent_progression.act import Step
    head = Step(action=ACQUIRING, via="urn:venue", want=want, urgency_after=0.1,
                predicts=predicted_reading(fern.me.acts_for, MOISTURE, 0.55))
    uri = keeper.adopt(head, want, "buy the water")
    rows = bindings(fern.intentions.query_union(f"""
SELECT ?a ?next ?p WHERE {{ <{uri}> orexis:step ?s . ?s orexis:fills ?a .
  OPTIONAL {{ ?s orexis:then ?next }} OPTIONAL {{ ?s orexis:predicts ?p }} }}"""))
    by_action = {r["a"]: r for r in rows}
    assert set(by_action) == {TENDERING, PRESENTING}
    assert by_action[TENDERING].get("next") and not by_action[TENDERING].get("p"), \
        "the tender leads to presenting and predicts nothing of the world"
    assert by_action[PRESENTING].get("p") and not by_action[PRESENTING].get("next"), \
        "presenting is last and carries the reading the search planned on"
    assert keeper.current(uri).action == TENDERING and keeper.in_progress(want) is not None


def test_a_won_round_walks_the_method_and_a_lost_one_lapses_it(monkeypatch):
    """The whole protocol through the ledger: the offer plans once and adopts the method; the
    bid goes out and the tender is held until a claim; the claim advances to presenting,
    held until the watch is live; the watch opens on the end. And a round that closes with
    no claim lapses the tender, which drops the plan and tells deliberation — the next offer
    is a new search, not a reaction."""
    from orexis_capability_market.terms import CLAIMED_AT
    from conftest import wired_markets
    fern = _fern(monkeypatch)
    keeper, want, market = fern.keeper, stake_of(fern).uri, wired_markets(fern)[0]
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 1
    assert keeper.current(keeper.standing(want=want)[0].uri).action == TENDERING
    assert [p.rsplit("#", 1)[-1] for _, _, p in keeper.held()] == ["answeredWhen"], \
        "the tender is held on its action's doneWhen: a claim on this venue"
    assert keeper.open_expectations(want) == [], "which is not a watch on the world"
    fern.deliver(f"{market.claim_topic}/fern", {"auction_id": "r1", "jti": "c1", "amount_l": 0.5, "debit": 0.2})
    claims = bindings(fern.beliefs.query_union(f"SELECT ?c WHERE {{ <{fern.me.uri}> market:holdsClaim ?c . ?c <{CLAIMED_AT}> ?t }}"))
    assert len(claims) == 1, "the claim is a fact in my graph"
    standing = keeper.standing(want=want)
    assert len(standing) == 1 and keeper.current(standing[0].uri).action == PRESENTING, "advanced on the claim"
    failed = fern.deliberator._plans_failed
    # a second, lost round: a new intention on the next offer, and its tender lapses at the close
    fern.deliver(market.offer_topic, {"auction_id": "r2", "closes_in_s": 30})
    for s in keeper.standing(want=want):
        if s.action == TENDERING:
            keeper.lapse(s.uri)                            # the round closed, no claim
            assert fern.deliberator._plans_failed == failed + 1, "a lost round is a plan that failed"
            assert all(x.uri != s.uri for x in keeper.standing(want=want)), "and its tail is dropped"


def test_a_method_of_methods_expands_flat_and_every_step_knows_its_filling(monkeypatch):
    """A member with a method of its own expands in turn; the ledger walks a flat chain; each
    step is `partOf` the filling it came from, and the parent stays in the ledger off the
    chain, so the tree is recoverable."""
    from orexis_agent_progression.act import Step
    from orexis_agent_progression.ontology import ACTIONS_GRAPH
    fern = _fern(monkeypatch)
    keeper, want = fern.keeper, stake_of(fern).uri
    T = "urn:toy#"
    fern.beliefs.update(f"""INSERT DATA {{ GRAPH <{ACTIONS_GRAPH}> {{
      <{T}Errand> a orexis:Action ; orexis:method ( <{T}Fetch> <{T}Return> ) .
      <{T}Fetch> a orexis:Action ; orexis:method ( <{T}Go> <{T}Grab> ) .
      <{T}Go> a orexis:Action . <{T}Grab> a orexis:Action . <{T}Return> a orexis:Action . }} }}""")
    uri = keeper.adopt(Step(action=T + "Errand", via=T + "parcel", want=want, urgency_after=0.1,
                            predicts=predicted_reading(fern.me.acts_for, MOISTURE, 0.55)),
                       want, "run the errand")
    rows = bindings(fern.intentions.query_union(f"""
SELECT ?a ?next ?pa ?ga ?p WHERE {{
  <{uri}> orexis:step ?s . ?s orexis:fills ?a .
  OPTIONAL {{ ?s orexis:then ?next }} OPTIONAL {{ ?s orexis:predicts ?p }}
  OPTIONAL {{ ?s orexis:partOf ?parent . ?parent orexis:fills ?pa .
             OPTIONAL {{ ?parent orexis:partOf ?grand . ?grand orexis:fills ?ga }} }} }}"""))
    by = {r["a"].rsplit("#", 1)[-1]: r for r in rows}
    assert set(by) == {"Go", "Grab", "Return"}, "flat: the walked steps, and only them"
    assert by["Go"]["pa"].endswith("Fetch") and by["Go"]["ga"].endswith("Errand"), \
        "Go is part of a Fetch filling, which is part of the Errand filling"
    assert by["Return"]["pa"].endswith("Errand") and by["Return"].get("p"), \
        "Return is the last member and carries the end the search planned on"
    assert by["Go"].get("next") and by["Grab"].get("next") and not by["Return"].get("next")
    assert keeper.current(uri).action == T + "Go" and keeper.current(uri).part_of, \
        "and the ledger's step knows its filling"

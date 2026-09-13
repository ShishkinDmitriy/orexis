"""A winner receives water at a time (#625) — the second half of
a-claim-is-water-at-a-time, held to the code.

The bid says when the water is wanted; the claim says from when it can be used; the presenting
of the claim is what an instant-bound want places at its instant, never the bid — the bid is
taken while a round is open, which is now or not at all. And a pass that stood at the latest
start and found nothing there stands at the present instead, where the round is.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import pursuit
from orexis_agent_progression.ontology import WORLD_GRAPH, beliefs_graph
from orexis_agent_progression.store import bindings
from orexis_capability_market.clearing import Claim
from orexis_capability_market.terms import ACQUIRING, PRESENTING, USABLE_FROM
from conftest import build_agent, genesis_store, open_round_for, wired_markets

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
FORESIGHT = "http://example.org/orexis/sensing#foresightS"
FALLING = 0.47          # 0.02 above the simulation fern's floor of 0.45, at 0.12 a day: four hours in a real day
HOURS = 3600.0


def _real_day(st) -> None:
    """These tests are about placement at the latest start, which needs a purchase that can
    land before the crossing. The simulation's own day is ten minutes, so a plant there
    crosses in a hundred seconds and a purchase lands in nine hundred — a day and a half of
    that world — and buying ahead is impossible (the-world-states-the-length-of-its-day).
    They stand in a real day, where the fern's crossing is four hours."""
    st.update(f"""DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?w orexis:secondsPerDay ?d }} }}
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?w orexis:secondsPerDay 86400 }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?w orexis:secondsPerDay ?d }} }}""")


def _fern(monkeypatch, moisture=FALLING, foresight=6 * HOURS):
    st = genesis_store({("fern", MOISTURE): moisture})
    _real_day(st)
    st.update(f"""INSERT DATA {{ GRAPH <{beliefs_graph("fern")}> {{
        <http://example.org/orexis/world/simulation#fern_agent> <{FORESIGHT}> {foresight} }} }}""")
    return build_agent("fern", st, monkeypatch)


def _stake(agent):
    return next(d for d in agent.pursuing()
                if getattr(d, "observed_property", None) == MOISTURE and not d.is_epistemic)


def test_a_pass_that_finds_nothing_at_the_latest_start_stands_at_the_present(monkeypatch):
    """The third row of #620's table, as the search's own road: the projected root sees no round
    — the one open now is a graph holding during its period, and the root stands past it — so
    the pass runs again from the present, finds Acquiring, and the plan is not placed, since
    the bid is taken now."""
    agent = _fern(monkeypatch)
    open_round_for(agent, "fern", seconds=60.0)
    root = _stake(agent)
    assert root.is_met
    plan = agent.deliberator.decide(root)
    assert plan is not None and [s.action for s in plan.steps] == [ACQUIRING], plan
    assert plan.placed_at is None, "found from the present: taken now, not placed"
    child = _stake(agent)
    assert child.holds_at is not None
    assert agent.deliberator._planners[child.uri]._root.landing == 0, "the pass stood at now"


def test_the_bid_says_when_the_water_is_wanted(monkeypatch):
    """Pursued, the tender goes out now, and it names the instant the fern intends to present:
    the want's instant less the pour the host's valve takes for the litres bid."""
    agent = _fern(monkeypatch)
    market = wired_markets(agent)[0]
    open_round_for(agent, "fern", seconds=60.0)
    root = _stake(agent)
    assert pursuit.pursue(agent, root) is not None
    bids = agent.sent.to(f"{market.bid_topic}/fern")
    assert bids, "the bid went out now, while the round is open"
    child = _stake(agent)
    wanted = datetime.fromisoformat(bids[-1]["wanted_at"])
    ahead = (child.holds_at - wanted).total_seconds()
    assert 0.0 <= ahead <= 600.0, f"the presenting instant is the want's, less the pour: {ahead}s"


def test_a_claim_with_a_window_places_the_presenting(monkeypatch):
    """The host granted a window from the instant asked for. The claim fact carries it, the
    keeper places the Presenting step on the scheduler until it opens, and nothing is presented
    before then."""
    agent = _fern(monkeypatch)
    market = wired_markets(agent)[0]
    open_round_for(agent, "fern", seconds=60.0)
    root = _stake(agent)
    uri = pursuit.pursue(agent, root)
    assert uri is not None
    child = _stake(agent)
    opens = datetime.now(timezone.utc) + timedelta(hours=3)
    agent.deliver(f"{market.claim_topic}/fern", {
        "auction_id": open_round_for.__name__ and None, "jti": "j-window", "sub": "fern",
        "amount_l": 0.5, "debit": 0.2,
        "usable_from": opens.isoformat(),
        "usable_until": (opens + timedelta(seconds=900)).isoformat()})
    held = bindings(agent.beliefs.query(f"""SELECT ?from WHERE {{ GRAPH <{beliefs_graph("fern")}> {{
        ?c <http://example.org/orexis/market#claimId> "j-window" ; <{USABLE_FROM}> ?from }} }}"""))
    assert held and datetime.fromisoformat(held[0]["from"]) == opens, "the fact carries from when it is usable"
    presenting = agent.keeper.standing(action=PRESENTING, want=child.uri)
    assert presenting, "the tender was answered and the plan advanced to presenting"
    assert agent.sent.to(f"{market.redeem_topic}/fern") == [], "nothing is presented before the window opens"
    assert not agent.keeper.ready(presenting[0].uri), "the step is placed at the claim's usable instant"
    assert presenting[0].uri in agent.keeper._deadlines, "and waits on the scheduler alone"


def test_the_host_refuses_a_presentation_before_the_window_opens(monkeypatch, caplog):
    """A claim usable in three hours, presented now: refused, and the claim stands — it is not
    spent, and the debt is not unserved, it is early."""
    import logging
    supplier = build_agent("supplier", genesis_store(), monkeypatch)
    host = supplier.hosting()
    opens = datetime.now(timezone.utc).timestamp() + 3 * HOURS
    host.held["j-early"] = Claim(sub="fern", permits="actuate:valve/fern", amount_l=0.5, debit=0.2,
                                 auction_id="r1", jti="j-early", exp=opens + 900.0, usable_from=opens,
                                 step=None)
    with caplog.at_level(logging.WARNING, logger="supplier.hosting"):
        host.on_redeem("fern", {"jti": "j-early", "sub": "fern"})
    assert "before its window opens" in caplog.text
    assert "j-early" in host.held, "refused, not spent: the claim stands until its window"

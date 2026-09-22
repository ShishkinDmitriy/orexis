"""A plant asks for a dose at an instant, and a round is the allocation under scarcity (#627)
— the fourth claim of a-claim-is-water-at-a-time, held to the code.

A want derived from a predicted crossing is met AT an instant. The bidder announces it where it
announces being low — the litres a bid would be sized to and the instant it intends to present
— once per want and instant. A host whose stock covers the ask at that instant, less what it
already owes to holders whose windows open by then, grants a claim with no round; one whose
stock does not convenes a round, exactly as a LOW does. And a claim held is what makes buying
available and the tender done, so the plan the granted plant makes is the presenting alone.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import pursuit
from orexis_agent_progression.ontology import PROGRESSION, picks_graph, obligations_graph
from orexis_agent_progression.store import bindings
from orexis_capability_market import rounds
from orexis_capability_market.terms import ACQUIRING, PRESENTING, TENDERING
from conftest import (build_agent, genesis_store, wired_event_topic, wired_hosted_markets,
                      wired_markets, wired_sensors)
from orexis_agent_progression.ontology import FORESEEN
from orexis_agent_progression import clock

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
STORED = "http://example.org/orexis/water#StoredLitres"
OWED_FROM = "http://example.org/orexis/market#owedFrom"
FALLING = 0.47          # 0.02 above the simulation fern's floor of 0.45, at 0.12 a day: below by five hours, so the crossing is an hour out
HOURS = 3600.0


def _fern(monkeypatch, moisture=FALLING):
    st = genesis_store({("fern", MOISTURE): moisture})
    return build_agent("fern", st, monkeypatch)


def _supplier(monkeypatch, level=3.0):
    """The simulation's supplier, its barrel at `level` litres inside its region of one to five."""
    return build_agent("supplier", genesis_store({("barrel1", STORED): level}), monkeypatch)


def _region_want(agent):
    return next(d for d in agent.wants() if MOISTURE in d.about)


def _foresee(agent):
    """The pass that derives the want met at the crossing — and finds nothing on the menu:
    no round is open and no claim is held, so a purchase cannot be planned yet."""
    desire = _region_want(agent)
    assert desire.is_met
    assert agent.deliberator.decide(desire) is None, "no round, no claim: nothing on the menu"
    child = _region_want(agent)
    assert child.desire == desire.uri and child.holds_at is not None
    return desire, child


def _read(agent, value=FALLING):
    agent.deliver(wired_sensors(agent)[0].reading_topic, {"moisture": value})


def _asks_of(agent):
    return [e for e in agent.sent.to(wired_event_topic(agent)) if "asks" in e]


def _ask(host, litres: float, hours: float, who: str = "fern"):
    wanted = datetime.now(timezone.utc) + timedelta(hours=hours)
    host.deliver(f"readings/{who}", {"agent": who, "property": MOISTURE, "asks": litres,
                                     "wanted_at": wanted.isoformat()})
    return wanted


def _claims_to(host, who: str):
    return host.sent.to(f"{wired_hosted_markets(host)[0].claim_topic}/{who}")


# --- the plant asks ---------------------------------------------------------------------------


def test_a_foreseen_crossing_is_asked_for_at_its_instant(monkeypatch):
    """The reading after the crossing was foreseen carries the ask out on the event topic: the
    litres a bid would be sized to, wanted at the want's instant less the pour."""
    agent = _fern(monkeypatch)
    desire, child = _foresee(agent)
    assert _asks_of(agent) == [], "nothing asked before the crossing was foreseen"
    _read(agent)
    (ask,) = _asks_of(agent)
    assert ask["agent"] == "fern" and ask["property"] == MOISTURE and ask["asks"] > 0
    ahead = (child.holds_at - datetime.fromisoformat(ask["wanted_at"])).total_seconds()
    assert 0.0 <= ahead <= 600.0, f"wanted at the want's instant, less the pour: {ahead}s"


def test_an_ask_goes_out_once_per_want_and_instant(monkeypatch):
    """Every reading re-runs the announcing; the ask for one instant is made once."""
    agent = _fern(monkeypatch)
    _foresee(agent)
    _read(agent)
    _read(agent)
    assert len(_asks_of(agent)) == 1


def test_a_plant_that_foresees_nothing_asks_for_nothing(monkeypatch):
    """Met, with no crossing foreseen, the reading announces no ask — the desire is never asked
    for; only a want met at an instant is."""
    agent = _fern(monkeypatch, moisture=0.60)
    desire = _region_want(agent)
    assert desire.is_met and agent.deliberator.decide(desire) is None
    assert _region_want(agent).holds_at is None, "no crossing inside the foresight: no want at an instant"
    _read(agent, 0.60)
    assert _asks_of(agent) == []


# --- the host answers -------------------------------------------------------------------------


def test_a_host_whose_stock_covers_the_ask_grants_a_claim_with_no_round(monkeypatch):
    """Three litres held, half a litre asked for in three hours, floor at one: granted — a claim
    usable from the instant asked for, no round, and a debt in the ledger carrying the window."""
    host = _supplier(monkeypatch, level=3.0)
    wanted = _ask(host, 0.5, hours=3)
    (claim,) = _claims_to(host, "fern")
    assert claim["amount_l"] == 0.5 and claim["auction_id"].startswith("ask-")
    assert abs((datetime.fromisoformat(claim["usable_from"]) - wanted).total_seconds()) < 1.0
    assert rounds.rounds_of(host) == [], "covered from stock: no round convened"
    rows = bindings(host.beliefs.query(f"""SELECT ?from WHERE {{
        ?o <http://example.org/orexis/market#forClaim> "{claim['jti']}" ; <{OWED_FROM}> ?from }}""",
        host.beliefs.graphs_of(*FORESEEN, at=clock.now())))
    assert rows and abs((datetime.fromisoformat(rows[0]["from"]) - wanted).total_seconds()) < 1.0


def test_a_host_convenes_a_round_where_the_asks_exceed_its_stock(monkeypatch):
    """Three litres held; one and a half asked for in an hour, granted; one more asked for in
    two — by then the barrel holds one and a half, less one is half, under its floor of one:
    not granted, a round convened, as a LOW convenes one."""
    host = _supplier(monkeypatch, level=3.0)
    _ask(host, 1.5, hours=1)
    assert len(_claims_to(host, "fern")) == 1 and rounds.rounds_of(host) == []
    _ask(host, 1.0, hours=2, who="tomato")
    assert _claims_to(host, "tomato") == [], "the second ask is not covered: the earlier grant is owed by then"
    assert len(rounds.rounds_of(host)) == 1, "scarcity: the round is the allocation"


def test_a_stranger_is_not_answered(monkeypatch):
    host = _supplier(monkeypatch, level=3.0)
    _ask(host, 0.5, hours=1, who="nobody")
    assert _claims_to(host, "nobody") == [] and rounds.rounds_of(host) == []


# --- the granted plant presents -------------------------------------------------------------


def _placed_instant_comes(agent, intention_uri: str) -> None:
    """The scheduler's path, without the wait: the step's placed instant rewritten as past,
    and the deadline taken as the scheduler would take it."""
    g = agent.keeper.graph
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    agent.intentions.update(f"""
DELETE {{ GRAPH <{g}> {{ ?act <{PROGRESSION}notBefore> ?was }} }}
INSERT {{ GRAPH <{g}> {{ ?act <{PROGRESSION}notBefore> "{past}"^^xsd:dateTime }} }}
WHERE  {{ GRAPH <{g}> {{ <{intention_uri}> <{PROGRESSION}by> ?act . ?act <{PROGRESSION}notBefore> ?was }} }}""")
    agent.keeper.lapse(intention_uri)


def test_a_granted_claim_makes_the_plan_the_presenting_alone(monkeypatch):
    """The claim the host granted on the ask arrives with nothing standing. Holding it, buying
    is available at every instant, so the pass standing at the latest start finds Acquiring
    and the plan is placed there; at its instant the tender is done by the claim held — no bid
    goes out, there is no round — and the presenting is placed at the claim's window."""
    agent = _fern(monkeypatch)
    desire, child = _foresee(agent)
    market = wired_markets(agent)[0]
    opens = datetime.now(timezone.utc) + timedelta(hours=3)
    agent.deliver(f"{market.claim_topic}/fern", {
        "auction_id": "ask-1234abcd", "jti": "j-ask", "sub": "fern", "amount_l": 0.5, "debit": 0.2,
        "usable_from": opens.isoformat(), "usable_until": (opens + timedelta(seconds=900)).isoformat()})
    uri = pursuit.pursue(agent, desire)
    assert uri is not None, "holding a claim, buying is on the menu with no round open"
    (tender,) = agent.keeper.standing(action=TENDERING, want=child.uri)
    assert tender.step.not_before is not None and tender.uri in agent.keeper._deadlines, \
        "found from the latest start: placed there, on the scheduler"
    assert agent.sent.to(f"{market.bid_topic}/fern") == [], "no bid went out: there is no round"
    _placed_instant_comes(agent, tender.uri)
    assert agent.keeper.standing(action=TENDERING, want=child.uri) == [], "the tender is done by the claim held"
    presenting = agent.keeper.standing(action=PRESENTING, want=child.uri)
    assert presenting, "the plan came to the presenting"
    assert agent.sent.to(f"{market.bid_topic}/fern") == [], "still no bid: nothing was tendered"
    assert not agent.keeper.ready(presenting[0].uri), "placed at the claim's window"
    assert agent.sent.to(f"{market.redeem_topic}/fern") == [], "nothing presented before it opens"


def test_a_claim_whose_window_closed_unpresented_is_no_longer_held(monkeypatch):
    """Holding a claim is what makes buying available and a tender done, so one left over past
    its window — its presenting dropped — is a graph whose period has ended (#645): the door
    hands it to nobody, the one sweep drops it, and a later tender is not done by it."""
    agent = _fern(monkeypatch)
    market = wired_markets(agent)[0]
    closed = datetime.now(timezone.utc) - timedelta(hours=1)
    agent.deliver(f"{market.claim_topic}/fern", {
        "auction_id": "ask-old", "jti": "j-old", "sub": "fern", "amount_l": 0.5, "debit": 0.2,
        "usable_from": (closed - timedelta(seconds=900)).isoformat(), "usable_until": closed.isoformat()})
    held = lambda at=None: bindings(agent.beliefs.query(  # noqa: E731
        f"SELECT ?c WHERE {{ <{agent.me.uri}> market:holdsClaim ?c }}",
        agent.beliefs.graphs_of(*FORESEEN, at=at or clock.now())))
    from orexis_capability_market.bidding import claim_graph
    assert held() == [], "its window closed before it was held: handed to nobody at any instant"
    assert claim_graph(agent.id, "j-old") in agent.beliefs.outdated(), "a graph whose period has ended"
    assert agent.upkeep.sweep() >= 1, "and the one sweep drops it"
    assert claim_graph(agent.id, "j-old") not in agent.beliefs.periods()
    assert agent.bidding()._claim_on(market.uri) is None

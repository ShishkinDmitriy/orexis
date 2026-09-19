"""A host predicts the arrivals it promised (#626) — the third claim of
a-claim-is-water-at-a-time, held to the code.

Every claim the host issued is a debt in its ledger, and since #625 a debt says from when its
holder may come. The vessel's drift reads those windows: its level at a future instant is what
it holds less what it owes to holders whose windows have opened by then, and the first window
at which that takes the level under the floor is the crossing. The host derives
the want and plans the refill from the present, where the upstream round is.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orexis_agent_deliberation import pursuit
from orexis_agent_progression.ontology import picks_graph, obligations_graph
from orexis_agent_progression.store import bindings
from orexis_capability_market.terms import ACQUIRING
from conftest import build_agent, genesis_store, open_round_for
from orexis_agent_progression.ontology import FORESEEN
from orexis_agent_progression import clock

STORED = "http://example.org/orexis/water#StoredLitres"
OWED_FROM = "http://example.org/orexis/market#owedFrom"
SUPPLIER = "http://example.org/orexis/world/simulation#supplier"
HOURS = 3600.0


def _supplier(monkeypatch, level=3.0):
    """The simulation's supplier, its barrel at `level` litres inside its region of one to five."""
    st = genesis_store({("barrel1", STORED): level})
    return build_agent("supplier", st, monkeypatch)


def _ower(agent):
    """The host's ledger — owing is the host's, not a capability of its own."""
    return agent.hosting().ledger


def _stock(agent, derived: bool = False):
    """The stock ROOT, or with `derived` the want standing under it — since every desire is
    derived the moment a claim arrives, both may be pursued at once."""
    return next(d for d in agent.pursuing()
                if getattr(d, "observed_property", None) == STORED and not d.is_epistemic
                and (d.derived_from is not None) == derived)


def _promise(agent, to: str, jti: str, litres: float, opens: datetime) -> None:
    """A claim the host issued to `to`, usable from `opens` for the venue's window."""
    _ower(agent).owe(to, jti, expires_at=(opens + timedelta(seconds=900)).timestamp(),
                     amount_l=litres, usable_from=opens.timestamp())


def test_a_debt_carries_from_when_its_holder_may_come(monkeypatch):
    """The window the host granted with the claim rides onto the debt — the predicted arrival."""
    agent = _supplier(monkeypatch)
    opens = datetime.now(timezone.utc) + timedelta(hours=1)
    _promise(agent, "fern", "j-from", 1.0, opens)
    rows = bindings(agent.beliefs.query(f"""SELECT ?from WHERE {{
        ?o <http://example.org/orexis/market#forClaim> "j-from" ; <{OWED_FROM}> ?from }}""",
        agent.beliefs.graphs_of(*FORESEEN, at=clock.now())))
    assert rows and abs((datetime.fromisoformat(rows[0]["from"]) - opens).total_seconds()) < 1.0


def test_the_vessel_crosses_its_floor_at_the_window_that_empties_it(monkeypatch):
    """Three litres held, one and a half owed in an hour, one more owed in two: after the first
    window the barrel holds one and a half — inside its region — and after the second half a
    litre, under its floor of one. The crossing is the start of the earliest prediction at
    which the stock reads unmet: the window from an hour to five hours out, whose far end holds
    half a litre (#643)."""
    agent = _supplier(monkeypatch, level=3.0)
    now = datetime.now(timezone.utc)
    root = _stock(agent)
    assert root.is_met and pursuit.crossing_of(agent, root.uri) is None, "nothing owed: no crossing"
    _promise(agent, "fern", "j1", 1.5, now + timedelta(hours=1))
    _promise(agent, "tomato", "j2", 1.0, now + timedelta(hours=2))
    crossing = pursuit.crossing_of(agent, root.uri)
    assert crossing is not None
    assert abs((crossing - (now + timedelta(hours=1))).total_seconds()) < 120, crossing


def test_a_host_that_foresees_the_crossing_plans_the_refill_from_the_present(monkeypatch):
    """The stock root derives a want met at the crossing; the pass at the
    latest start finds no upstream round holding then, stands at the present where one is open,
    and plans Acquiring from the city — the refill ahead of the arrivals, from the claims alone,
    with nothing presented yet."""
    agent = _supplier(monkeypatch, level=3.0)
    now = datetime.now(timezone.utc)
    _promise(agent, "fern", "j1", 1.5, now + timedelta(hours=1))
    _promise(agent, "tomato", "j2", 1.0, now + timedelta(hours=2))
    open_round_for(agent, "supplier", seconds=60.0)
    #  EVERY DESIRE IS DERIVED THE MOMENT A CLAIM ARRIVES (judge-desires-then-derive-wants):
    #  the stock root was judged met at the present and unmet at the crossing, the want stands
    #  already, and the container presents the root under it.
    from orexis_agent_deliberation.judgments import find_judgments
    child = _stock(agent, derived=True)
    root = child.derived_from
    judged = [r for r in find_judgments(agent.beliefs.engine)[agent.me.uri] if r["desire"] == root]
    assert next(r["met"] for r in judged if not r.get("at")) == "true", "met at the present"
    assert any(r["met"] == "false" for r in judged if r.get("at")), "unmet at a crossing"
    plan = agent.deliberator.decide(child)
    assert plan is not None and [s.action for s in plan.steps] == [ACQUIRING], plan
    assert plan.placed_at is None, "found from the present, where the round is: taken now"
    child = _stock(agent, derived=True)
    assert child.derived_from == root and child.state == "unmet"


def test_a_discharged_debt_is_not_an_arrival(monkeypatch):
    """A debt paid is history: the crossing moves out with it."""
    agent = _supplier(monkeypatch, level=3.0)
    now = datetime.now(timezone.utc)
    root = _stock(agent)
    _promise(agent, "fern", "j1", 1.5, now + timedelta(hours=1))
    _promise(agent, "tomato", "j2", 1.0, now + timedelta(hours=2))
    assert pursuit.crossing_of(agent, root.uri) is not None
    _ower(agent).discharge("j1")
    assert pursuit.crossing_of(agent, root.uri) is None, "one and a half litres paid: the second window leaves two"

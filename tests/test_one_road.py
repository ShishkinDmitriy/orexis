"""One road derives every want, and the market's debts come by it too.

The ledger used to mint the want beside the debt — a second deriver, with a second trigger,
reaching the same graph family by a different door (#675). It writes the DEBT and a PREDICTION
now: that the debt lapses at its deadline, a graph holding from that instant. The host's desire,
*no overdue debts*, carries a met-test whose violations are debts with a lapse in view; asked at
the prediction's start, its rows name the debt and the instant, and the pursuit road mints the
want that must hold AT it — exactly as a want under a region desire is minted from a reading and
what the drift predicts of it. The ledger then speaks for the road's want: how far its claim's
window has run, whom it is owed to, whether the holder has asked.

See knowledge/decisions/one-road-derives-every-want.md.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from conftest import build_agent, genesis_store
from orexis_agent_deliberation import pursuit
from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import bindings

HOUR = 3600.0


def _host(monkeypatch, stock: float | None = None):
    monkeypatch.setenv("OREXIS_WORLD", "simulation")
    seeded = {("barrel1", "http://example.org/orexis/water#StoredLitres"): stock} if stock else None
    agent = build_agent("supplier", genesis_store(seeded, world="simulation"), monkeypatch)
    ledger = next(m for m in agent.modules if m.__class__.__name__ == "HostingModule").ledger
    return agent, ledger, f"{agent.me.uri}.no_overdue_debts"


def _want_for(agent, jti):
    return next((w for w in agent.wants.find_all_pursued()
                 if any(a.endswith(f"obligation.{jti}") for a in w.about)), None)


def test_a_claim_arriving_writes_a_debt_and_a_prediction_and_the_road_mints_the_want(monkeypatch):
    """The whole of it: a claim arrives; the ledger writes the debt and predicts its lapse and
    asks the road; the desire's select names the debt at that instant; the road mints one want
    about that debt, holding at the deadline; and the ledger speaks for it."""
    agent, ledger, root = _host(monkeypatch)
    assert agent.wants.find_all_pursued() == []
    deadline = time.time() + HOUR
    debt = ledger.owe("fern", "jti-1", expires_at=deadline, amount_l=1.0)
    assert debt is not None

    #  THE LEDGER WROTE NO WANT: the debt is an instance, typed as nothing the road reads,
    #  and the want that stands is the ROAD's — in deliberation's family, derived from the
    #  desire, minted on the ledger's ask and not by its hand.
    assert not bindings(agent.beliefs.query_union(
        f"SELECT ?t WHERE {{ <{debt}> a ?t . FILTER(STRSTARTS(STR(?t), '{OREXIS}')) }}")), \
        "the debt row carries no kernel type — it is not a want"
    [want] = agent.wants.find_all_by_desire(root)          # every desire derives; this one's
    assert want.desire == root and want.about == (debt,)
    assert want.uri.startswith(root + ".pursued.obligation.")
    assert abs(datetime.fromisoformat(want.holds_at).timestamp() - deadline) < 1.0

    #  A LAPSE IS NOT IN VIEW YET — the prediction holds from the deadline, and the desire's
    #  select names the debt at that instant and at no other
    assert agent.beliefs.prediction_graphs() == []
    [w] = pursuit.witnesses_of(agent, root)
    assert w.instance == debt and w.about == debt, "the row is about the debt itself (sh:this)"
    assert abs(w.at.timestamp() - deadline) < 1.0

    #  THE LEDGER SPEAKS FOR IT: its claim, standing and not yet askable
    [judged] = ledger.obligations()
    assert judged.uri == want.uri and judged.claim == "jti-1"
    assert judged.state == "standing" and not judged.pursuable
    presented = next(j for j in agent.pursuing() if j.uri == want.uri)
    assert presented.claim == "jti-1" and presented.derived_from == root, \
        "the choir's judgment, under the road's provenance"


def test_presenting_makes_the_roads_want_pursuable_and_paying_withdraws_its_ground(monkeypatch):
    agent, ledger, root = _host(monkeypatch)
    ledger.owe("fern", "jti-2", expires_at=time.time() + HOUR, amount_l=1.0)
    pursuit.judge_desires(agent)
    pursuit.derive_wants(agent)
    ledger.demanded("jti-2")
    [judged] = ledger.obligations()
    assert judged.state == "demanded" and judged.pursuable, "the holder asked"

    ledger.discharge("jti-2")
    assert ledger.obligations() == [], "a paid debt is judged by nobody"
    assert pursuit.witnesses_of(agent, root) == [], "and will not lapse: the prediction went"


def test_a_second_claim_is_a_second_want_and_the_first_stands(monkeypatch):
    """Per INSTANCE, which the greenhouse could not show: two debts are two focus nodes of the
    desire's shape, so two clusters and two wants, each holding at its own deadline — the
    second is not filtered away by the first's crossing. And standing on either want tops up
    nothing: the road is idempotent over what already stands."""
    agent, ledger, root = _host(monkeypatch)
    ledger.owe("fern", "jti-3", expires_at=time.time() + HOUR, amount_l=1.0)
    ledger.owe("fern", "jti-4", expires_at=time.time() + 2 * HOUR, amount_l=1.0)
    first, second = _want_for(agent, "jti-3"), _want_for(agent, "jti-4")
    assert first is not None and second is not None, "one want per debt"
    assert datetime.fromisoformat(second.holds_at) > datetime.fromisoformat(first.holds_at), \
        "each at its own deadline"

    presented = next(j for j in agent.pursuing() if j.uri == first.uri)
    assert pursuit.handed(agent, presented).uri == first.uri
    pursuit.judge_desires(agent)
    assert pursuit.derive_wants(agent) == [], "nothing new to mint"
    assert {w.uri for w in agent.wants.find_all_by_desire(root)} == {first.uri, second.uri}


def test_what_was_foreseen_has_arrived_when_the_holder_asks_before_the_lapse(monkeypatch):
    """A claim with a deadline is a want AT its lapse — the road read that off the prediction —
    and a plan for a want at an instant is placed to land at it (#619). Then the holder
    presents, an hour early. The debt is in violation NOW, and a want still saying "hold at
    the lapse" would have the serve placed at the deadline less the pour while the buyer
    waits: hosting's own presentation path served now, and a pass from `pursuing()` did
    not. The road re-mints the want with no instant, under the same name, and a pass from
    either door serves now."""
    from orexis_agent_progression import clock

    agent, ledger, root = _host(monkeypatch, stock=3.0)
    deadline = time.time() + HOUR
    debt = ledger.owe("fern", "jti-5", expires_at=deadline, amount_l=0.5)
    [foreseen] = agent.wants.find_all_pursued()
    assert foreseen.holds_at is not None, "minted at the lapse"

    ledger.demanded("jti-5")
    [now] = agent.wants.find_all_pursued()
    assert now.uri == foreseen.uri and now.about == (debt,), "the same want, re-minted"
    assert now.holds_at is None, "at no instant: the holder is waiting"
    pursuit.judge_desires(agent)
    assert pursuit.derive_wants(agent) == [], "and the road is idle again"

    presented = next(j for j in agent.pursuing() if j.uri == now.uri)
    assert presented.holds_at is None and presented.pursuable
    plan = agent.deliberator.decide(presented)
    assert plan is not None and [s.action.rsplit("#", 1)[-1] for s in plan.steps] == ["Serving"]
    assert plan.placed_at is None or plan.placed_at <= clock.now(), \
        "placed from the present, not at the lapse less the pour"


def test_the_tick_marks_a_presented_debt_and_leaves_an_unpresented_one_standing(monkeypatch):
    """The tick marks every want that may be acted on and skips what nobody may act on yet —
    a debt its holder has not presented stands hot and unmarked, since a pass on it would
    decide nothing (#132). It used to skip DEBTS, by kind, and leave a presented one the
    search could not serve to hosting's own wake-ups alone; a presented debt is a want like
    any other now, reconsidered on the tick until the world changes the answer."""
    from orexis_agent_deliberation import deliberator as deliberation

    agent, ledger, root = _host(monkeypatch, stock=3.0)
    ledger.owe("fern", "jti-6", expires_at=time.time() + HOUR, amount_l=0.5)
    ledger.owe("fern", "jti-7", expires_at=time.time() + HOUR, amount_l=0.5)
    ledger.demanded("jti-7")
    asked, presented = {j.claim: j for j in ledger.obligations()}, {}
    assert not asked["jti-6"].pursuable and asked["jti-7"].pursuable

    pursued = []
    monkeypatch.setattr(deliberation.pursuit, "pursue", lambda a, j, **k: pursued.append(j.uri))
    agent.deliberator.deliberate_on_gaps()
    assert asked["jti-7"].uri in pursued, "presented: reconsidered like any other want"
    assert asked["jti-6"].uri not in pursued, "unpresented: standing, hot, and not decided on"

    marked = []
    monkeypatch.setattr(agent.reviser, "note", lambda uri, judgment=None, **k: marked.append(uri))
    agent.deliberator.tick()
    assert asked["jti-7"].uri in marked and asked["jti-6"].uri not in marked

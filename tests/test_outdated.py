"""Every want sourced at a time is a graph with a period, and one sweep drops what is
outdated (#645) — item 3 of a-root-holds-always-and-an-outdated-graph-is-dropped, held to the
code.

A round, a held claim, a cooling row, a debt, a pursued child and a prediction are each a graph
holding during a period. The door hides one past its end from every reader, so nothing waits
on a sweep; one sweep — in progression's housekeeping tick and at boot — drops every such graph
whatever its kind, and the owner of the kind, told `orexis:outdated` first, writes the verdict
it leaves. No package keeps a sweep of its own.
"""
from __future__ import annotations

from datetime import timedelta

from orexis_agent_deliberation import pursuit
from orexis_agent_deliberation.derive_wants import mint
from orexis_agent_progression import clock
from orexis_capability_market import rounds
from orexis_capability_market.bidding import claim_graph
from orexis_capability_market.ower import obligation_graph
from orexis_capability_sensing import predictions, readings
from conftest import (MOISTURE, build_agent, genesis_store, stake_of, wired_markets, write_reading)
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import PREDICTION
from orexis_agent_progression.ontology import KNOWN

STORED = "http://example.org/orexis/water#StoredLitres"


def test_one_sweep_drops_a_round_a_claim_and_a_cooling_row_past_their_ends(monkeypatch):
    """Three kinds the market used to sweep each by hand — invisible to every reader before
    the sweep, gone after one, and no sweep of the market's own left."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    market = wired_markets(fern)[0]
    now = clock.now()
    rounds.open_round(fern, market.uri, "old", 2.0, 0.4, now - timedelta(seconds=5),
                      opened_at=now - timedelta(seconds=35))
    rounds.convened(fern, market.uri, cooldown_s=60.0, now=now - timedelta(seconds=61))
    closed = now - timedelta(hours=1)
    fern.deliver(f"{market.claim_topic}/fern", {
        "auction_id": "ask-old", "jti": "j-old", "sub": "fern", "amount_l": 0.5, "debit": 0.2,
        "usable_from": (closed - timedelta(seconds=900)).isoformat(), "usable_until": closed.isoformat()})
    ended = {rounds.round_graph(fern.id, "old"), rounds.cooling_graph(fern.id, market.uri),
             claim_graph(fern.id, "j-old")}
    assert ended <= set(fern.beliefs.periods()), "held, though ended — nothing has swept yet"
    assert ended <= set(fern.beliefs.outdated())
    assert not (ended & set(fern.beliefs.graphs_of(*KNOWN, at=clock.now()))), "and a reader at this instant is handed none of them"
    assert rounds.rounds_of(fern) == [] and fern.bidding()._claim_on(market.uri) is None
    assert fern.upkeep.sweep() >= 3
    assert not (ended & set(fern.beliefs.periods())), "gone, classification and period with them"
    assert not any(hasattr(m, "sweep") for m in fern.modules), "no module keeps a sweep of its own"


def test_a_pursued_child_and_a_prediction_past_their_ends_are_swept(monkeypatch):
    """The mind's own timed graphs: a child derived for an instant that has passed, and a
    ladder predicted from a reading two days old."""
    agent = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.12}, world="loner"), monkeypatch)
    root = stake_of(agent).uri
    child = mint(agent, root, holds_at=clock.now() - timedelta(days=1))
    assert child is not None
    write_reading(agent, 0.12, MOISTURE, age_s=2 * 86400)
    reading = readings.current_reading(agent.beliefs.reader(PUBLIC), agent.me.acts_for, MOISTURE)
    ladder = predictions.write(agent, agent.me.uri, agent.me.acts_for, MOISTURE, reading, 600.0, 45.0)
    assert ladder
    ended = {agent.wants.graph_of(agent.id, child), *ladder}
    assert ended <= set(agent.beliefs.outdated())
    assert pursuit.child_of(agent, root) is None, "a child past its instant is pursued by nobody"
    assert agent.beliefs.graphs_of(PREDICTION, at=clock.now()) == []
    assert agent.upkeep.sweep() >= len(ended)
    assert not (ended & set(agent.beliefs.periods()))


def test_a_debt_lapsing_unserved_leaves_its_verdict_and_no_want(monkeypatch):
    """The ledger keeps the verdict, not the want: a debt whose window closed unpresented is
    no want in the modality and no row `owed` lists; the sweep drops its graph after the
    ledger's keeper writes `market:lapsedAt` into the record, beside a debt paid, so a debt
    paid and a debt forgotten never look alike."""
    supplier = build_agent("supplier", genesis_store({("barrel1", STORED): 3.0}), monkeypatch)
    ledger = supplier.hosting().ledger
    now = clock.now()
    ledger.owe("fern", "j-lapse", expires_at=(now - timedelta(seconds=60)).timestamp(), amount_l=1.0)
    ledger.owe("tomato", "j-paid", expires_at=(now - timedelta(seconds=30)).timestamp(), amount_l=0.5)
    ledger.discharge("j-paid")
    assert ledger.owed() == [], "past their windows: the door hands neither to anybody"
    assert not any(getattr(d, "claim", None) in ("j-lapse", "j-paid") for d in supplier.pursuing()), \
        "and neither is a want in the modality"
    assert {obligation_graph(supplier.id, "j-lapse"), obligation_graph(supplier.id, "j-paid")} \
        <= set(supplier.beliefs.outdated())
    assert supplier.upkeep.sweep() >= 2
    settled = {r["jti"]: r for r in ledger.settled()}
    assert settled["j-lapse"].get("lapsed") and not settled["j-lapse"].get("paid")
    assert settled["j-paid"].get("paid") and not settled["j-paid"].get("lapsed")
    assert obligation_graph(supplier.id, "j-lapse") not in supplier.beliefs.periods()


def test_a_restart_finds_what_lapsed_while_it_was_down_and_sweeps_it_first(monkeypatch):
    """A graph classified at its own write keeps its class across a boot, so the process that
    comes up finds the debt outdated, drops it before its first pass, and holds the verdict."""
    supplier = build_agent("supplier", genesis_store({("barrel1", STORED): 3.0}), monkeypatch)
    ledger = supplier.hosting().ledger
    #  A WINDOW WIDE ENOUGH TO OUTLIVE THE ASSERT BELOW. It was one second, and the assert
    #  that the debt still stands then raced it: under `-n auto` on a loaded machine the
    #  window closed first and the door handed the debt to nobody, which reads exactly like
    #  the defect this test is about. What the test is FOR is the boot that comes after the
    #  window closes, and three seconds proves that as well as one.
    ledger.owe("fern", "j-down", expires_at=(clock.now() + timedelta(seconds=3)).timestamp(), amount_l=1.0)
    assert len(ledger.owed()) == 1
    import time
    time.sleep(3.2)                       # the window closes while the process is "down"
    reborn = build_agent("supplier", supplier.beliefs, monkeypatch)   # boots on the same store, and sweeps
    assert reborn.hosting().ledger.owed() == []
    assert obligation_graph(reborn.id, "j-down") not in reborn.beliefs.periods(), "swept at boot"
    assert any(r["jti"] == "j-down" and r.get("lapsed") for r in reborn.hosting().ledger.settled())

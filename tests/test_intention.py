"""The intention: a commitment with a lifecycle, kept in a ledger of the agent's own.

Phase 3 of knowledge/decisions/an-intention-is-an-amortised-deliberation.md. Nothing here tests
new behaviour, because there is none — the point of the phase is that `bidding.pending` and a
bid awaiting its claim were already intentions, and are now rows with an adoption, a
resolution and a reason. What IS new, and is tested hardest, is the patience: within it a second
impulse to do the same thing is absorbed rather than re-decided, which is the amortisation the
whole roadmap is named for.

Driven through real agents delivering real messages, like test_round, because the writers are
the bidder's handlers and a ledger nobody writes to proves nothing.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from agent.world import load_self
from packages.capability.intention import intentions_graph
from packages.capability.intention.terms import ACQUIRE, KEEPING, OBSERVE

from conftest import MOISTURE, build_agent, genesis_store

FERN = "http://example.org/agora#fern_agent"


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


def keeper_of(agent):
    return next(m for m in agent.modules if m.name == "intention")


def market_of(agent):
    return agent.me.markets[0]


# --- who keeps, and who has nothing to keep ---------------------------------

def test_a_stake_and_a_lever_grant_keeping():
    """Fern wants (its plant states ranges) and can act (a market, a schedulable board)."""
    q = genesis_store().query
    assert KEEPING in load_self(q, "fern").capabilities
    assert KEEPING in load_self(q, "succulent").capabilities


def test_no_stake_means_nothing_to_commit_to():
    """A commitment is to reduce a named gap, and an agent without one keeps no ledger. The
    supplier used to be this test's example — levers everywhere, no stake — until arc 2 gave
    it the barrel's want and its valves became a lever's other half. The sensing world's fern
    still shows the fact cleanly (sensors and no wants), and the supplier now shows it only
    when its stake is taken away."""
    assert KEEPING in load_self(genesis_store().query, "supplier").capabilities
    assert KEEPING not in load_self(
        genesis_store(world="sensing").query, "fern").capabilities

    from agent import genesis, loader
    from agent.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH

    st = genesis_store()
    st.update(f"""DELETE WHERE {{ GRAPH <{WORLD_GRAPH}> {{
        <http://example.org/agora/world/simulation#supplier>
            <http://example.org/agora#actsFor> ?o }} }}""")
    st.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        st.update(genesis.substitute(rule.read_text(), st))
    assert KEEPING not in load_self(st.query, "supplier").capabilities


# --- the two writers that exist, writing ------------------------------------

def test_waiting_on_a_sensor_is_a_recorded_commitment(make):
    """The state `pending` always carried, now a row: adopted when the wait begins, satisfied
    when the look comes back — at which point the bid flies, which adopts the acquire."""
    fern = make("fern")  # no fresh reading, so the offer starts a wait
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    keeper = keeper_of(fern)
    standing = keeper.standing(means=OBSERVE)
    assert len(standing) == 1 and standing[0].observed_property == MOISTURE

    fern.deliver(fern.me.sensors[0].reading_topic, {"moisture": 0.10})
    assert keeper.standing(means=OBSERVE) == []       # the look came back
    assert len(keeper.standing(means=ACQUIRE)) == 1   # and the bid it fed is now committed


def test_a_wait_the_auction_outlives_is_dropped_with_the_reason(make):
    fern = make("fern")
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    keeper = keeper_of(fern)
    fern.bidding().give_up()
    assert keeper.standing(means=OBSERVE) == []
    # the resolution carries why — a commitment abandoned without a reason is one forgotten
    from agent.store import bindings
    rows = bindings(fern.store.query(
        "SELECT ?why WHERE { GRAPH <%s> { ?i intention:outcome \"dropped\" ; "
        "intention:becauseOf ?why } }" % intentions_graph("fern")))
    assert any("auction closed first" in r["why"] for r in rows)


def test_a_claim_satisfies_the_acquisition(make):
    fern = make("fern", _reading(0.10))
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    keeper = keeper_of(fern)
    assert len(keeper.standing(means=ACQUIRE)) == 1

    fern.deliver(f"{market.claim_topic}/fern", {"amount_l": 0.5, "debit": 0.2})
    assert keeper.standing(means=ACQUIRE) == []


def _reading(value):
    return genesis_store({"fern": value})


# --- the patience: the amortisation itself ----------------------------------

def test_within_its_patience_a_second_impulse_is_absorbed(make):
    """One commitment spans several rounds. A second auction while an acquire stands does not
    adopt a second acquire — the ledger says what the agent is ABOUT, not what messages flew —
    and that refusal is what will make an LLM deliberator affordable: committed means not
    re-decided."""
    fern = make("fern", _reading(0.10))
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    fern.deliver(market.offer_topic, {"auction_id": "r2", "closes_in_s": 3})
    keeper = keeper_of(fern)
    assert len(keeper.standing(means=ACQUIRE)) == 1
    # both bids still flew — in phase 3 the ledger records and never gates
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 2


def test_past_its_patience_a_new_adoption_supersedes(make):
    """A commitment the world never answered must not stand forever. Past the patience, a new
    adoption resolves the old as dropped — with the outwaiting recorded — and stands itself."""
    fern = make("fern", _reading(0.10))
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)  # everything is instantly stale
    first = keeper.adopt(ACQUIRE, MOISTURE, "first")
    second = keeper.adopt(ACQUIRE, MOISTURE, "second")
    assert first and second and first != second
    standing = keeper.standing(means=ACQUIRE)
    assert [s.uri for s in standing] == [second]

    from agent.store import bindings
    rows = bindings(fern.store.query(
        "SELECT ?why WHERE { GRAPH <%s> { <%s> intention:outcome \"dropped\" ; "
        "intention:becauseOf ?why } }" % (intentions_graph("fern"), first)))
    assert any("outwaited" in r["why"] for r in rows)


def test_the_patience_is_read_from_the_agents_own_beliefs(make):
    assert keeper_of(make("fern")).beliefs.patience_s == 120


# --- privacy and the health series ------------------------------------------

def test_intentions_are_nobody_elses_to_read(make):
    """Not public: the bid is the public face of an intention to acquire, never the intention.
    An unqualified pattern — what any peer's query amounts to — finds nothing."""
    fern = make("fern", _reading(0.10))
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert intentions_graph("fern") not in fern.store.public_graphs()
    from agent.store import bindings
    assert bindings(fern.store.query(
        "SELECT ?i WHERE { ?i a intention:Intention }")) == []


def test_the_agent_reports_what_stands_and_how_old(make):
    fern = make("fern", _reading(0.10))
    keeper = keeper_of(fern)
    fresh = keeper.reports()
    assert fresh["intentions_standing"] == 0
    assert "oldest_intention_s" not in fresh
    # the end-verdict counters ride along since #131 — all quiet on a fresh agent
    assert (fresh["expectations_open"], fresh["expectations_met"],
            fresh["expectations_unmet"], fresh["affordances_suspect"]) == (0, 0, 0, 0)
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    reported = keeper.reports()
    assert reported["intentions_standing"] == 1
    assert reported["oldest_intention_s"] >= 0.0


# --- the story told to the operator (#125) ----------------------------------

def test_every_transition_is_told_to_the_metrics_with_its_reason(make):
    """The ledger stays the record; the buffer is the projection the reporting capability
    drains into the agent's own bucket, where Grafana draws it over the series. Tags carry
    LOCAL names — a dashboard is filtered by a person, not by a resolver."""
    fern = make("fern", _reading(0.10))
    keeper = keeper_of(fern)
    fern.metrics.take_events()
    uri = keeper.adopt(ACQUIRE, MOISTURE, "bid 0.4L to close my deficit")
    keeper.satisfy(ACQUIRE, MOISTURE, "claim for 0.4L at a debit of 0.29")
    events = fern.metrics.take_events()
    assert [(kind, tags) for _, kind, _, tags in events] == [
        ("adopted", {"means": "Acquire", "property": "SoilMoisture"}),
        ("satisfied", {"means": "Acquire", "property": "SoilMoisture"})]
    assert [text for _, _, text, _ in events] == [
        "bid 0.4L to close my deficit", "claim for 0.4L at a debit of 0.29"]

    # and the end's verdict, which is the payoff line of the whole arc (#131)
    assert keeper.expect(uri, MOISTURE, "the dose owes a rise")
    fern.metrics.take_events()
    keeper.on_reading_recorded(fern.me.acts_for, MOISTURE, 0.50)
    verdicts = fern.metrics.take_events()
    assert [kind for _, kind, _, _ in verdicts] == ["end-met"]
    assert "moved from" in verdicts[0][2]


# --- gap-driven deliberation (#208) -----------------------------------------

TEMP = "http://example.org/agora/water#AirTemperature"
MOIST = "http://example.org/agora/water#SoilMoisture"


def test_sensing_notices_what_it_has_never_seen(make):
    """The archetype gap contribution: a freshly born fern has two sensors and no
    observations, so sensing reports both channels as gaps — noticing only, adopting
    nothing, which is the deciding/keeping boundary said as a hook."""
    fern = make("fern")
    sensing = next(m for m in fern.modules if m.name == "subscribing")
    assert {p for _, p in sensing.gaps()} == {MOIST, TEMP}


def test_the_tick_puts_marketless_watching_in_the_ledger(make):
    """The hole the sovereign's question exposed, closed: deliberation used to run only when
    the market knocked, so fern's thermometer — a stake, a sensor, and no market that could
    ever relieve it — never appeared in the intention ledger at all. The keeper's tick turns
    sensing's gap into the one deliberator's Observe and commits it: the watching is now a
    commitment the sovereign can ask for, and a reading arriving resolves it, whoever
    caused the look."""
    fern = make("fern")
    keeper = next(m for m in fern.modules if m.name == "intention")
    keeper.deliberate_on_gaps()
    standing = {(s.means.rsplit("#", 1)[-1], s.observed_property) for s in keeper.standing()}
    assert ("Observe", TEMP) in standing, "the marketless property is watched ON THE RECORD"
    assert ("Observe", MOIST) in standing

    fern.deliver(fern.me.sensors[0].reading_topic, {"temperature": 21.0})
    left = {s.observed_property for s in keeper.standing()}
    assert TEMP not in left, "the look happened — satisfied, whoever triggered it"
    assert MOIST in left, "the other channel still owes a reading"


def test_a_second_tick_within_patience_is_absorbed(make):
    """The rate bound is the patience, by construction rather than by a second mechanism:
    ticking again while the Observe stands adopts nothing new — adopt() refuses — so the
    ledger holds one commitment per gap, however often anyone notices it."""
    fern = make("fern")
    keeper = next(m for m in fern.modules if m.name == "intention")
    keeper.deliberate_on_gaps()
    first = len(keeper.standing())
    keeper.deliberate_on_gaps()
    assert len(keeper.standing()) == first


def test_only_the_keeper_writes_the_intentions_graph():
    """The boundary, pinned as source: gaps() notices and propose() decides, but the ledger
    has ONE writer. A module reaching for the intentions graph by name would be a second
    keeper — the welded chain returning with a pen — and this scan is what makes that a
    failing test instead of a review comment."""
    from pathlib import Path

    from agent import loader

    offenders = []
    for path in sorted(loader.PACKAGES_ROOT.rglob("*.py")):
        if "capability/intention" in str(path):
            continue
        if "intentions_graph" in path.read_text():
            offenders.append(str(path))
    assert not offenders, f"a second pen on the ledger: {offenders}"

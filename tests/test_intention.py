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
from orexis_agent_progression.graphs import intentions_graph
from orexis_capability_market.terms import ACQUIRING
from orexis_capability_sensing.terms import OBSERVING

from conftest import sensing_of, stake_of, MOISTURE, build_agent, genesis_store, wired_markets, wired_sensors, reading_of

FERN = "http://example.org/orexis#fern_agent"


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


def keeper_of(agent):
    return next(m for m in agent.modules if m.name == "intention")


def market_of(agent):
    return wired_markets(agent)[0]


# --- who keeps, and what became of "who has nothing to keep" -----------------

def test_every_agent_keeps_a_ledger_and_the_stake_is_what_needs_a_patience(make):
    """`intention:Keeping` was granted by a stake AND a lever, and two tests stood here to prove
    each half. The grant is gone: `Agent.__init__` already built an intention STORE for every
    agent while the thing that WRITES it was a grant, and a modality nobody may write is not a
    modality. Commitment is not plug-in-able.

    What survives is the SHAPE, and it is narrower on purpose. `ag:KeeperShape` targets the
    stake alone — an agent that holds a want that is not merely about knowing must state a
    patience within the constitutional bounds. The lever half could not follow it into the
    kernel without the kernel naming three packages' predicates, and a lever is an instance
    anyway; the stake's PREMISE (a subject stating what it needs) is sensing's sentence now,
    so the shape names the want and not the premise.

    So: everyone keeps, and the stake is what obliges you to say how patiently."""
    from agent.validate import validate_agent

    fern = make("fern")
    assert fern.keeper is not None
    assert any(m.name == "intention" for m in fern.modules)

    #  The shape still bites where it always did: a stake with a patience outside the bounds
    #  is refused, which is the piece a beliefs file can actually get wrong.
    fern.beliefs.update(f"""DELETE {{ GRAPH <{fern.beliefs.graph}> {{
        <{fern.me.uri}> <http://example.org/orexis#patienceS> ?p }} }}
      INSERT {{ GRAPH <{fern.beliefs.graph}> {{
        <{fern.me.uri}> <http://example.org/orexis#patienceS> 2 }} }}
      WHERE  {{ GRAPH <{fern.beliefs.graph}> {{
        <{fern.me.uri}> <http://example.org/orexis#patienceS> ?p }} }}""")
    fern.desires.rebuild()
    with pytest.raises(Exception):
        validate_agent(fern.beliefs, "fern", fern.me.uri, fern.me.capabilities,
                       desires=fern.desires)


# --- the two writers that exist, writing ------------------------------------

def test_waiting_on_a_sensor_is_a_recorded_commitment(make):
    """The state `pending` always carried, now a row: adopted when the wait begins, satisfied
    when the look comes back — at which point the bid flies, which adopts the acquire."""
    fern = make("fern")  # no fresh reading, so the offer starts a wait
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    keeper = keeper_of(fern)
    standing = keeper.standing(action=OBSERVING)
    #  The look is committed FOR THE FRESHNESS WANT — knowing first, sensing's rule — and
    #  the ledger says which want, not which property (the-stake-is-sensings-want).
    looked_for = next(w for w in sensing_of(fern).wants_about(MOISTURE) if w.is_epistemic)
    assert len(standing) == 1 and standing[0].want == looked_for.uri

    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.10})
    assert keeper.standing(action=OBSERVING) == []       # the look came back
    assert len(keeper.standing(action=ACQUIRING)) == 1   # and the bid it fed is now committed


def test_a_wait_the_auction_outlives_keeps_the_look_and_lets_the_round_go(make):
    """The look used to be adopted FOR the auction and dropped with it. Since the bidder asks
    execution for its look, the commitment is to the freshness want — a reading is still owed
    after the round closes, whoever first wanted it — so the look STANDS, the round's row goes,
    and the reading that lands is what resolves it (sensing satisfies its own means now)."""
    from orexis_capability_market import rounds

    fern = make("fern")
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    keeper = keeper_of(fern)
    assert len(keeper.standing(action=OBSERVING)) == 1, "the look was committed for the round"
    fern.bidding().give_up()
    assert len(keeper.standing(action=OBSERVING)) == 1, "and it stands — a reading is still owed"
    assert rounds.rounds_of(fern) == [], "the round is over for me"
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.2})
    assert keeper.standing(action=OBSERVING) == [], "the look happened"


def test_a_claim_satisfies_the_acquisition(make):
    fern = make("fern", _reading(0.10))
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    keeper = keeper_of(fern)
    assert len(keeper.standing(action=ACQUIRING)) == 1

    fern.deliver(f"{market.claim_topic}/fern", {"amount_l": 0.5, "debit": 0.2})
    assert keeper.standing(action=ACQUIRING) == []


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
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    fern.deliver(market.offer_topic, {"auction_id": "r2", "closes_in_s": 30})
    keeper = keeper_of(fern)
    assert len(keeper.standing(action=ACQUIRING)) == 1
    # both bids still flew — in phase 3 the ledger records and never gates
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == 2


def test_past_its_patience_a_new_adoption_supersedes(make):
    """A commitment the world never answered must not stand forever. Past the patience, a new
    adoption resolves the old as dropped — with the outwaiting recorded — and stands itself."""
    fern = make("fern", _reading(0.10))
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)  # everything is instantly stale
    first = keeper.adopt(ACQUIRING, stake_of(fern).uri, "first")
    second = keeper.adopt(ACQUIRING, stake_of(fern).uri, "second")
    assert first and second and first != second
    standing = keeper.standing(action=ACQUIRING)
    assert [s.uri for s in standing] == [second]

    from orexis_agent_progression.store import bindings
    rows = bindings(fern.beliefs.query(
        "SELECT ?why WHERE { GRAPH <%s> { <%s> ag:outcome \"dropped\" ; "
        "ag:becauseOf ?why } }" % (intentions_graph("fern"), first)))
    assert any("outwaited" in r["why"] for r in rows)


def test_the_patience_is_read_from_the_agents_own_beliefs(make):
    assert keeper_of(make("fern")).beliefs.patience_s == 120


# --- privacy and the health series ------------------------------------------

def test_intentions_are_nobody_elses_to_read(make):
    """Not public: the bid is the public face of an intention to acquire, never the intention.
    An unqualified pattern — what any peer's query amounts to — finds nothing."""
    fern = make("fern", _reading(0.10))
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    assert intentions_graph("fern") not in fern.beliefs.public_graphs()
    from orexis_agent_progression.store import bindings
    assert bindings(fern.beliefs.query(
        "SELECT ?i WHERE { ?i a ag:Intention }")) == []


def test_the_agent_reports_what_stands_and_how_old(make):
    fern = make("fern", _reading(0.10))
    keeper = keeper_of(fern)
    fresh = keeper.reports()
    assert fresh["intentions_standing"] == 0
    assert "oldest_intention_s" not in fresh
    # the end-verdict counters ride along since #131 — all quiet on a fresh agent
    assert (fresh["expectations_open"], fresh["expectations_met"],
            fresh["expectations_unmet"], fresh["affordances_suspect"]) == (0, 0, 0, 0)
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 30})
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
    stake = stake_of(fern).uri
    uri = keeper.adopt(ACQUIRING, stake, "bid 0.4L to close my deficit")
    keeper.satisfy(ACQUIRING, stake, "claim for 0.4L at a debit of 0.29")
    events = fern.metrics.take_events()
    assert [(kind, tags) for _, kind, _, tags in events] == [
        ("adopted", {"means": "Acquiring", "want": "desire.fern.SoilMoisture"}),
        ("satisfied", {"means": "Acquiring", "want": "desire.fern.SoilMoisture"})]
    assert [text for _, _, text, _ in events] == [
        "bid 0.4L to close my deficit", "claim for 0.4L at a debit of 0.29"]

    # and the end's verdict, which is the payoff line of the whole arc (#131)
    assert keeper.expect(uri, "the dose owes a rise", rises=True,
                         baseline=reading_of(fern, MOISTURE))
    fern.metrics.take_events()
    keeper.judge(stake, 0.50)
    verdicts = fern.metrics.take_events()
    assert [kind for _, kind, _, _ in verdicts] == ["end-met"]
    assert "moved from" in verdicts[0][2]


# --- gap-driven deliberation (#208) -----------------------------------------

TEMP = "http://example.org/orexis/water#AirTemperature"
MOIST = "http://example.org/orexis/water#SoilMoisture"


def test_the_tick_puts_marketless_watching_in_the_ledger(make):
    """The hole the sovereign's question exposed, closed: deliberation used to run only when
    the market knocked, so fern's thermometer — a stake, a sensor, and no market that could
    ever relieve it — never appeared in the intention ledger at all. The keeper's tick turns
    sensing's gap into the one deliberator's Observe and commits it: the watching is now a
    commitment the sovereign can ask for, and a reading arriving resolves it, whoever
    caused the look."""
    fern = make("fern")
    keeper = next(m for m in fern.modules if m.name == "intention")
    keeper.agent.deliberator.deliberate_on_gaps()
    #  The ledger names the WANT; which property a want is about is sensing's to say.
    about = {w.uri: w.observed_property for w in sensing_of(fern).desires()}
    standing = {(s.action.rsplit("#", 1)[-1], about.get(s.want)) for s in keeper.standing()}
    assert ("Observing", TEMP) in standing, "the marketless property is watched ON THE RECORD"
    assert ("Observing", MOIST) in standing

    fern.deliver(wired_sensors(fern)[0].reading_topic, {"temperature": 21.0})
    left = {about.get(s.want) for s in keeper.standing()}
    assert TEMP not in left, "the look happened — satisfied, whoever triggered it"
    assert MOIST in left, "the other channel still owes a reading"


def test_a_second_tick_within_patience_is_absorbed(make):
    """The rate bound is the patience, by construction rather than by a second mechanism:
    ticking again while the Observe stands adopts nothing new — adopt() refuses — so the
    ledger holds one commitment per gap, however often anyone notices it."""
    fern = make("fern")
    keeper = next(m for m in fern.modules if m.name == "intention")
    keeper.agent.deliberator.deliberate_on_gaps()
    first = len(keeper.standing())
    keeper.agent.deliberator.deliberate_on_gaps()
    assert len(keeper.standing()) == first


def test_only_the_keeper_writes_the_intentions_graph():
    """The boundary, pinned as source: gaps() notices and propose() decides, but the ledger
    has ONE writer. A module reaching for the intentions graph by name would be a second
    keeper — the welded chain returning with a pen — and this scan is what makes that a
    failing test instead of a review comment.

    IT SCANNED ONLY `packages/`, and the kernel had held a second pen the whole time:
    `orexis_agent_progression/intentions.py` names the graph to migrate a pre-split volume's ledger into the
    modality's own room, and `agent/genesis.py` names it to classify it. Both are legitimate
    and neither is a keeper — but the guard could not see them, because it looked only at the
    tree the pen was not in. Now it scans BOTH trees and the exemptions are named with reasons,
    which is the difference between a boundary and a boundary nobody checked half of."""
    from assembly import loader

    #  Named one by one, with the reason each is allowed to hold the pen. An exemption that
    #  could be met by accident is a hole; these are three files and three arguments.
    ALLOWED = {
        "keeper.py":     "the keeper itself — the one writer this test exists to protect",
        "graphs.py":     "mints the IRI; naming a graph is what this file is for",
        "intentions.py": "the MODALITY: it owns the store and moves a pre-split volume's rows "
                         "into the room of its own, once. It writes the container, never a row",
        "genesis.py":    "classifies the graph in the provenance graph — a statement ABOUT it",
    }
    offenders = []
    for path in loader.sources("*.py"):
        if path.name in ALLOWED:
            continue
        if "intentions_graph" in path.read_text():
            offenders.append(str(path.relative_to(loader.REPO_ROOT)))
    assert not offenders, f"a second pen on the ledger: {offenders}"


def test_the_tick_survives_an_agent_that_has_seen_things(make):
    """The collision regression: desire has ALWAYS had a `gaps()` — the rich desired/sensed
    dict — and the choir hook briefly shared its name, so the tick iterated property IRIs as
    pairs and died unpacking a string. Invisible to the original test because a fresh agent
    has no observations and desire's dict was empty; the bench, where observations exist on
    every stake, crashed per tick. So: see something first, then tick."""
    fern = make("fern")
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.2, "temperature": 21.0})
    keeper = next(m for m in fern.modules if m.name == "intention")
    keeper.agent.deliberator.deliberate_on_gaps()  # must not raise — that is the whole test


# --- a commitment names the desire it serves (step 3) -------------------------

SERVING = "http://example.org/orexis/market#Serving"


def test_two_debts_about_one_property_no_longer_collide(make):
    """The collision the mind review turned up, closed before it could go live.

    A dealer owing water to fern AND to tomato holds two Apply commitments about one property.
    Keyed by (means, property) alone they are indistinguishable: satisfying one satisfies
    both, and the patience absorbs the second impulse as if it were the first — the same shape
    as an observation keyed by its subject alone. Keyed by the GOAL they are two debts, and
    paying one leaves the other standing, which is what a creditor would expect.
    """
    supplier = make("supplier")
    keeper = next(m for m in supplier.modules if m.name == "intention")
    to_fern = "http://example.org/orexis#obligation.fern-claim"
    to_tomato = "http://example.org/orexis#obligation.tomato-claim"

    assert keeper.adopt(SERVING, to_fern, "owed to fern")
    assert keeper.adopt(SERVING, to_tomato, "owed to tomato"), \
        "a second debt about the same property is a second debt, not the same impulse"
    assert len(keeper.standing(action=SERVING)) == 2

    keeper.satisfy(SERVING, to_fern, "fern's dose went out")
    left = keeper.standing(action=SERVING)
    assert len(left) == 1, "paying one debt must not discharge the other"


def test_a_commitment_is_keyed_by_its_want_and_absorbed_by_it(make):
    """The ledger keys on (action, want) and nothing else — the property is not a key the
    kernel holds any more (the-stake-is-sensings-want). A second impulse toward the same want
    within patience is absorbed; the same action toward ANOTHER want is a second commitment."""
    fern = make("fern")
    keeper = next(m for m in fern.modules if m.name == "intention")
    stake = stake_of(fern).uri
    keeper.adopt(OBSERVING, stake, "look, for the stake")
    assert keeper.adopt(OBSERVING, stake, "again, within patience") is None
    assert len(keeper.standing(action=OBSERVING, want=stake)) == 1
    assert keeper.adopt(OBSERVING, "urn:another-want", "look, for something else")
    assert len(keeper.standing(action=OBSERVING)) == 2


def test_an_old_row_naming_an_action_is_rebuilt_as_an_act(make):
    """A ledger written before an-act-is-a-filled-action pointed `ag:by` at the ACTION node and
    kept `ag:through` on the intention. At the keeper's construction such a row is rebuilt: an
    act node fills the action, the lever moves onto it, and `ag:by` names the act — so a reader
    of the ledger sees one shape whatever the volume's age, and the migration finds nothing
    to do the second time."""
    from orexis_agent_progression import ledger
    from orexis_agent_progression.ontology import AG

    fern = make("fern")
    keeper = keeper_of(fern)
    keeper.agent.intentions.update(f"""INSERT DATA {{ GRAPH <{keeper.graph}> {{
        <{AG}intent_fern_old1> a <{AG}Intention> ;
            <{AG}pursues> <{stake_of(fern).uri}> ;
            <{AG}by> <{ACQUIRING}> ;
            <{AG}through> <urn:old-venue> ;
            <{AG}adoptedAt> "2026-08-01T00:00:00+00:00"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")
    assert ledger.migrate_ledger_acts(keeper.agent.intentions, keeper.graph) == 1
    old = next(s for s in keeper.standing(action=ACQUIRING) if s.uri.endswith("old1"))
    assert old.act.action == ACQUIRING and old.act.via == "urn:old-venue"
    assert ledger.migrate_ledger_acts(keeper.agent.intentions, keeper.graph) == 0, \
        "idempotent — a row already naming an act is left alone"


def test_the_ledger_holds_the_act_sized_and_windowed(make):
    """What the plan's head committed to is written whole: the action it fills, the lever, the
    quantity the taker sized, and the window — read back as one `Act`, which is what an actor
    is handed when the trigger changes and the decision does not."""
    from datetime import datetime, timezone
    from orexis_agent_progression.act import Act

    fern = make("fern")
    keeper = keeper_of(fern)
    closes = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    act = Act(action=ACQUIRING, via="urn:venue", quantity=0.4, not_after=closes)
    keeper.adopt(act, stake_of(fern).uri, "bid 0.4L, not after the round closes")
    standing = keeper.standing(action=ACQUIRING)[0]
    assert (standing.act.action, standing.act.via, standing.act.quantity,
            standing.act.not_after) == (ACQUIRING, "urn:venue", 0.4, closes)

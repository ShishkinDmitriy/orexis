"""The end, judged apart from the means — issue #131's spine, driven through real agents.

The defect these exist to keep closed: an Acquire used to resolve when the VOUCHER arrived, and
nothing ever checked whether the gap moved. An agent whose water never reached the pot bought,
recorded satisfied, and bought again forever — transaction confirmed, outcome never audited.
Confidently dumb, structurally. Now the voucher opens a WATCH: baseline copied into the ledger
(the sensed graph keeps only the current witness), the promised direction copied from the
domain's own statement (#127), and the verdict lands beside the outcome as a separate fact.
"""

from __future__ import annotations

import logging
from dataclasses import replace

import pytest

from packages.capability.intention.terms import ACQUIRE

from conftest import MOISTURE, build_agent, genesis_store


@pytest.fixture
def thirsty(monkeypatch):
    """Fern with a fresh 0.30 on record — everything needed to bid, win, and be watched."""
    return build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)


def keeper_of(agent):
    return next(m for m in agent.modules if m.name == "intention")


def market_of(agent):
    return agent.me.markets[0]


def win(agent, auction="r1", amount=0.5, debit=0.2):
    """One full acquire: offer in, bid out, voucher back."""
    market = market_of(agent)
    agent.deliver(market.offer_topic, {"auction_id": auction, "closes_in_s": 3})
    agent.deliver(f"{market.voucher_topic}/fern", {"amount_l": amount, "debit": debit})


# --- the watch opens where the means resolves --------------------------------

def test_a_voucher_opens_a_watch_with_the_baseline_in_the_row(thirsty):
    """Satisfied is the MEANS; the end gets its own record: where the property stood, which way
    the domain promises it moves, and by when. The baseline is copied into the ledger because
    the sensed graph upserts — the before of any before/after survives nowhere else."""
    win(thirsty)
    keeper = keeper_of(thirsty)
    watches = keeper.open_expectations(MOISTURE)
    assert len(watches) == 1
    watch = watches[0]
    assert watch.baseline == 0.30
    assert watch.direction.endswith("Raises")   # copied from the domain's #127 statement
    assert watch.means == ACQUIRE


def test_opening_the_watch_asks_for_a_look(thirsty):
    """`sense_now` at adoption, so the freshest possible before is on record and the first
    after arrives as soon as the board can manage."""
    before = sum(1 for t, p, r in thirsty.sent if p.get("sense"))
    win(thirsty)
    assert sum(1 for t, p, r in thirsty.sent if p.get("sense")) > before


# --- the verdict: met, unmet, and never both ---------------------------------

def test_the_dose_landing_meets_the_end(thirsty):
    """Movement past the baseline in the promised direction, before the deadline — met, early
    is fine, that is the dose landing. The watch closes and the row now carries BOTH facts:
    outcome satisfied (the voucher) and endMet true (the world answered)."""
    win(thirsty)
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"value": 0.42})
    keeper = keeper_of(thirsty)
    assert keeper.open_expectations() == []
    assert keeper.reports()["expectations_met"] == 1
    assert keeper.reports()["expectations_unmet"] == 0


def test_movement_the_wrong_way_proves_nothing_before_the_deadline(thirsty):
    """A dose may land late; drying continues meanwhile. Falling readings inside the horizon
    leave the watch open rather than judging early — unmet is a verdict about the DEADLINE."""
    win(thirsty)
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"value": 0.29})
    assert len(keeper_of(thirsty).open_expectations()) == 1


def test_the_deadline_passing_unmet_is_the_false_knowledge_datum(monkeypatch):
    """The graph said this lever raises this property; the act was honoured; the property never
    moved. satisfied-and-UNMET, the signature nothing could record before #131."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)   # the horizon is now
    win(fern)
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.28})   # still falling
    assert keeper.open_expectations() == []
    reported = keeper.reports()
    assert reported["expectations_unmet"] == 1
    assert reported["expectations_met"] == 0


# --- the verification watch: attention follows the unverified -----------------

def test_an_open_watch_is_maximum_urgency_and_a_verdict_releases_it(thirsty):
    """The two processes run at different speeds: evaporation is fractions per day, a dose
    lands in seconds — and the naive loop relaxes attention exactly when the dose needs
    watching, because the value improves. An open expectation IS urgency; perception's
    ordinary max-of-answers does the rest, and the cadence round-trips: tight while the watch
    is on, back to the gap's own answer the moment it resolves."""
    keeper = keeper_of(thirsty)
    p = thirsty.subscribing()
    calm = p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55)

    win(thirsty)
    assert keeper.urgency(thirsty.me.acts_for, MOISTURE, 0.55) == 1.0
    # maximum urgency earns the agent's OWN fast cadence — the floor is a clamp, not a target
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == p.beliefs.fast_sleep_s

    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"value": 0.42})   # dose lands
    assert keeper.urgency(thirsty.me.acts_for, MOISTURE, 0.42) is None
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == calm


# --- the flag: suspicious after N, never auto-retracted -----------------------

def test_an_affordance_that_never_pays_becomes_suspect(monkeypatch, caplog):
    """Three acquisitions, three honoured vouchers, three deadlines passed with the pot still
    drying: the pair (Acquire, SoilMoisture) is flagged — a warning in the log, a line in the
    health series — and nothing is retracted, because what to do about a belief that is not
    paying is a decision, not a reflex. The agent must end up FLAGGED, not looping unmarked."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)

    value = 0.30
    with caplog.at_level(logging.WARNING):
        for auction in ("r1", "r2", "r3"):
            win(fern, auction=auction)
            value -= 0.01                                    # the world keeps refusing
            fern.deliver(fern.me.sensors[0].reading_topic, {"value": round(value, 2)})

    assert keeper.reports()["expectations_unmet"] == 3
    assert keeper.reports()["affordances_suspect"] == 1
    assert [pair for pair in keeper.suspects()
            if pair[0] == ACQUIRE and pair[1] == MOISTURE]
    assert "AFFORDANCE SUSPECT" in caplog.text


def test_one_success_resets_the_suspicion(monkeypatch):
    """Consecutive, not cumulative: an affordance that mostly pays is noisy, not false."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)

    win(fern, auction="r1")
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.29})   # unmet
    win(fern, auction="r2")
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.40})   # met — the reset
    win(fern, auction="r3")
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.39})   # unmet

    assert keeper.reports()["expectations_unmet"] == 2
    assert keeper.reports()["affordances_suspect"] == 0

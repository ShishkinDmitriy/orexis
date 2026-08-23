"""The end, judged apart from the means — issue #131's spine, driven through real agents.

The defect these exist to keep closed: an Acquire used to resolve when the CLAIM arrived, and
nothing ever checked whether the gap moved. An agent whose water never reached the pot bought,
recorded satisfied, and bought again forever — transaction confirmed, outcome never audited.
Confidently dumb, structurally. Now the claim opens a WATCH: baseline copied into the ledger
(the sensed graph keeps only the current witness), the promised direction copied from the
domain's own statement (#127), and the verdict lands beside the outcome as a separate fact.
"""

from __future__ import annotations

import logging
from dataclasses import replace

import pytest

from packages.capability.intention.terms import ACQUIRE, ACTUATE as _ACTUATE

from agent.store import bindings
from packages.capability.intention.terms import DEADLINE_AT

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
    """One full acquire: offer in, bid out, claim back."""
    market = market_of(agent)
    agent.deliver(market.offer_topic, {"auction_id": auction, "closes_in_s": 3})
    agent.deliver(f"{market.claim_topic}/fern", {"amount_l": amount, "debit": debit})


# --- the watch opens where the means resolves --------------------------------

def test_a_claim_opens_a_watch_with_the_baseline_in_the_row(thirsty):
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
    outcome satisfied (the claim) and endMet true (the world answered)."""
    win(thirsty)
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.42})
    keeper = keeper_of(thirsty)
    assert keeper.open_expectations() == []
    assert keeper.reports()["expectations_met"] == 1
    assert keeper.reports()["expectations_unmet"] == 0


def test_movement_the_wrong_way_proves_nothing_before_the_deadline(thirsty):
    """A dose may land late; drying continues meanwhile. Falling readings inside the horizon
    leave the watch open rather than judging early — unmet is a verdict about the DEADLINE."""
    win(thirsty)
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.29})
    assert len(keeper_of(thirsty).open_expectations()) == 1


def test_the_deadline_passing_unmet_is_the_false_knowledge_datum(monkeypatch):
    """The graph said this lever raises this property; the act was honoured; the property never
    moved. satisfied-and-UNMET, the signature nothing could record before #131."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)   # the horizon is now
    win(fern)
    fern.deliver(fern.me.sensors[0].reading_topic, {"moisture": 0.28})   # still falling
    assert keeper.open_expectations() == []
    reported = keeper.reports()
    assert reported["expectations_unmet"] == 1
    assert reported["expectations_met"] == 0


# --- the verification watch: attention follows the unverified -----------------

def test_an_open_watch_is_maximum_urgency_and_a_verdict_releases_it(thirsty):
    """The two processes run at different speeds: evaporation is fractions per day, a dose
    lands in seconds — and the naive loop relaxes attention exactly when the dose needs
    watching, because the value improves. An open expectation IS urgency; sensing's
    ordinary max-of-answers does the rest, and the cadence round-trips: tight while the watch
    is on, back to the gap's own answer the moment it resolves."""
    keeper = keeper_of(thirsty)
    p = thirsty.subscribing()
    calm = p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55)

    win(thirsty)
    assert keeper.urgency(thirsty.me.acts_for, MOISTURE, 0.55) == 1.0
    # maximum urgency earns the agent's OWN fast cadence — the floor is a clamp, not a target
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == p.beliefs.fast_sleep_s

    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.42})   # dose lands
    assert keeper.urgency(thirsty.me.acts_for, MOISTURE, 0.42) is None
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == calm


# --- the flag: suspicious after N, never auto-retracted -----------------------

def test_an_affordance_that_never_pays_becomes_suspect(monkeypatch, caplog):
    """Three acquisitions, three honoured claims, three deadlines passed with the pot still
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
            fern.deliver(fern.me.sensors[0].reading_topic, {"moisture": round(value, 2)})

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
    fern.deliver(fern.me.sensors[0].reading_topic, {"moisture": 0.29})   # unmet
    win(fern, auction="r2")
    fern.deliver(fern.me.sensors[0].reading_topic, {"moisture": 0.40})   # met — the reset
    win(fern, auction="r3")
    fern.deliver(fern.me.sensors[0].reading_topic, {"moisture": 0.39})   # unmet

    assert keeper.reports()["expectations_unmet"] == 2
    assert keeper.reports()["affordances_suspect"] == 0


# --- the claim waits for the watch (#132) -----------------------------------

def test_a_claim_is_held_until_the_watch_is_live(thirsty):
    """Never spend a dose you cannot watch land. The claim adopts an Apply — a held claim —
    and nothing is presented while readings arrive without the #135 stamp; the first reading
    acknowledged at the fast cadence is proof the board heard the tightening, and THAT is when
    the claim goes out, the Apply resolves, and the expectation opens with a baseline the hold
    did not age."""
    from packages.capability.intention.terms import APPLY

    market = market_of(thirsty)
    keeper = keeper_of(thirsty)
    thirsty.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    thirsty.deliver(f"{market.claim_topic}/fern",
                    {"jti": "v1", "amount_l": 0.5, "debit": 0.2})

    assert thirsty.sent.to(f"{market.redeem_topic}/fern") == [], \
        "winning must present nothing — the watch is not live"
    assert len(keeper.standing(means=APPLY)) == 1
    assert keeper.open_expectations() == []          # the dose is not imminent yet

    # a reading arrives WITHOUT the ack — the board has not heard the tightening
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.29})
    assert thirsty.sent.to(f"{market.redeem_topic}/fern") == []

    # and one acknowledged at the fast cadence — the watch is provably live
    fast = thirsty.subscribing().beliefs.fast_sleep_s
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.29, "sleep_s": fast})
    presented = thirsty.sent.to(f"{market.redeem_topic}/fern")
    assert presented and presented[-1]["jti"] == "v1"
    assert keeper.standing(means=APPLY) == []
    watches = keeper.open_expectations(MOISTURE)
    assert len(watches) == 1 and watches[0].baseline == 0.29


def test_the_bounded_wait_redeems_blind_rather_than_never(thirsty):
    """Old firmware that never acks, a board mid-sleep on a long cadence — a watch that cannot
    be confirmed within one full cycle is not going to be, and a dose delayed forever is worse
    than a dose unobserved. The deadline presents the claim and says it ran blind."""
    market = market_of(thirsty)
    thirsty.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    thirsty.deliver(f"{market.claim_topic}/fern",
                    {"jti": "v2", "amount_l": 0.5, "debit": 0.2})
    assert thirsty.sent.to(f"{market.redeem_topic}/fern") == []

    thirsty.bidding()._present_blind()
    presented = thirsty.sent.to(f"{market.redeem_topic}/fern")
    assert presented and presented[-1]["jti"] == "v2"


def test_a_held_claim_is_maximum_urgency(thirsty):
    """The hold is the watch one step earlier: the dose is coming the moment the watch is live,
    and the watch becomes live by exactly this urgency reaching the board. Claim → tight;
    presentation → the expectation takes over the same answer without a gap."""
    market = market_of(thirsty)
    p = thirsty.subscribing()
    thirsty.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    thirsty.deliver(f"{market.claim_topic}/fern",
                    {"jti": "v3", "amount_l": 0.5, "debit": 0.2})
    assert keeper_of(thirsty).urgency(thirsty.me.acts_for, MOISTURE, 0.55) == 1.0
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == p.beliefs.fast_sleep_s


# --- the margin: the world answers above the grain (#165) ---------------------

def test_a_breath_of_grain_past_the_baseline_is_not_the_world_answering(thirsty):
    """The live incident, replayed: a watch was closed by +0.001 of instrument grain two
    seconds before its dose landed, and the closed watch let the same gap be bought twice
    (#167). A movement counts only when commensurate with the act: metFraction (0.25) of the
    expected delta (0.5 L through 2.0 L-per-fraction = 0.25) is 0.0625, and grain clears
    nothing."""
    win(thirsty)
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.301})
    keeper = keeper_of(thirsty)
    assert len(keeper.open_expectations()) == 1, "grain must not close a watch"
    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.37})
    assert keeper.open_expectations() == []
    assert keeper.reports()["expectations_met"] == 1


def test_the_row_carries_how_far_the_act_should_move_it(thirsty):
    """The act sizes its own effect: 0.5 L through the same conversion the bid was priced
    with. Copied into the row like the baseline, so the verdict needs no join at reading time."""
    win(thirsty, amount=0.5)
    watch = keeper_of(thirsty).open_expectations(MOISTURE)[0]
    assert watch.expected_delta == pytest.approx(0.25)


def test_an_act_that_cannot_size_itself_keeps_the_exact_crossing(thirsty):
    """No delta stated, no margin demanded — the pre-noise verdict stays legal for whatever
    cannot say how far it should move the world."""
    keeper = keeper_of(thirsty)
    uri = keeper.adopt(ACQUIRE, MOISTURE, "an act of unknowable size")
    assert keeper.expect(uri, MOISTURE, "no delta stated")
    keeper.on_reading_recorded(thirsty.me.acts_for, MOISTURE, 0.301)
    assert keeper.open_expectations() == []
    assert keeper.reports()["expectations_met"] == 1


# --- while my own dose is unanswered, I do not buy again (#167) ---------------

def test_no_new_purchase_while_my_own_dose_is_unanswered(thirsty, caplog):
    """The double-buy, refused: the dose may have landed inside my sensor's sleep, and even a
    fresh look can race a valve that dispenses over half a minute. The bid is DECLINED, not
    gated — a judgment read off the ledger — and the world answering frees the very next round."""
    market = market_of(thirsty)
    win(thirsty)                                        # watch open, dose in flight
    bids = len(thirsty.sent.to(f"{market.bid_topic}/fern"))
    with caplog.at_level(logging.INFO, logger="fern.bidding"):
        thirsty.deliver(market.offer_topic, {"auction_id": "r2", "closes_in_s": 3})
    assert len(thirsty.sent.to(f"{market.bid_topic}/fern")) == bids, \
        "a phantom deficit was priced while my own dose was unanswered"
    assert "my own dose has not answered yet" in caplog.text

    thirsty.deliver(thirsty.me.sensors[0].reading_topic, {"moisture": 0.42})   # the world answers
    thirsty.deliver(market.offer_topic, {"auction_id": "r3", "closes_in_s": 3})
    assert len(thirsty.sent.to(f"{market.bid_topic}/fern")) == bids + 1


def test_a_dose_past_its_deadline_frees_the_bidder(monkeypatch):
    """Bounded, exactly as the cede's comment promises: an unanswered dose past the watch's
    own deadline is the false-knowledge case (#131's), and it must not also freeze the wallet."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)   # the deadline is now
    market = market_of(fern)
    win(fern)
    bids = len(fern.sent.to(f"{market.bid_topic}/fern"))
    fern.deliver(market.offer_topic, {"auction_id": "r2", "closes_in_s": 3})
    assert len(fern.sent.to(f"{market.bid_topic}/fern")) == bids + 1


# --- the window is the physics, not the patience (#247) ----------------------

def test_the_watch_runs_until_the_dose_lands_and_a_reading_could_show_it(monkeypatch):
    """The seam this docstring used to name — "the deadline is the patience; the dose and the
    physics could derive a better one" — closed.

    Patience was never WRONG, only unrelated: it is how long an agent waits before re-deciding,
    not how long the physics takes. Holding a dose to it judged a valve at 120s while the pot's
    own sensor reported every 600 — a false UNMET manufactured by a clock, and one that feeds
    `suspectAfter`, which is how an honest lever comes to be marked a liar.

    Both halves are asserted because both are load-bearing. The landing is the act's own, from
    its effect rule; the seeing is how stale a reading may be before this agent distrusts it,
    which is the cadence it commanded plus its own grace. A window that dropped either would be
    too short exactly when the equipment is slow.
    """
    from datetime import datetime, timezone

    gardener = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.10}, world="loner"),
                           monkeypatch)
    keeper = keeper_of(gardener)
    sensing = gardener.provider("http://example.org/orexis/sensing#SensingCapability")
    seeing = float(sensing.stale_after_s(gardener.me.acts_for, MOISTURE))

    uri = keeper.adopt(_ACTUATE, MOISTURE, "a dose is on its way")
    before = datetime.now(timezone.utc).timestamp()
    assert keeper.expect(uri, MOISTURE, "50 seconds of pouring", expected_delta=0.1,
                         lands_after_s=50.0)

    rows = bindings(gardener.beliefs.query(f"""
SELECT ?d WHERE {{ GRAPH <{keeper.graph}> {{ <{uri}> <{DEADLINE_AT}> ?d }} }}"""))
    window = datetime.fromisoformat(rows[0]["d"]).timestamp() - before
    assert abs(window - (50.0 + seeing)) < 2.0, (
        f"the watch should run for the dose (50s) plus how long seeing takes ({seeing}s), "
        f"and it ran for {window:.0f}s")
    assert window != pytest.approx(keeper.beliefs.patience_s, abs=2.0) or seeing + 50 == \
        keeper.beliefs.patience_s, "and not for the patience, which is a different question"


def test_an_act_that_cannot_size_itself_keeps_the_patience(monkeypatch):
    """The fallback, and it is the same shape as `expected_delta`'s: a caller that cannot say
    passes nothing and keeps exactly the behaviour it had. A buyer is the real case — it holds
    a claim on somebody else's valve and cannot ask its own rules how long that valve stays
    open, so patience is the only honest bound it has."""
    from datetime import datetime, timezone

    gardener = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.10}, world="loner"),
                           monkeypatch)
    keeper = keeper_of(gardener)
    uri = keeper.adopt(_ACTUATE, MOISTURE, "something is on its way")
    before = datetime.now(timezone.utc).timestamp()
    assert keeper.expect(uri, MOISTURE, "bought from someone else's valve", expected_delta=0.1)

    rows = bindings(gardener.beliefs.query(f"""
SELECT ?d WHERE {{ GRAPH <{keeper.graph}> {{ <{uri}> <{DEADLINE_AT}> ?d }} }}"""))
    window = datetime.fromisoformat(rows[0]["d"]).timestamp() - before
    assert abs(window - keeper.beliefs.patience_s) < 2.0

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

from orexis_capability_market.terms import ACQUIRING, TENDERING, PRESENTING
from orexis_capability_actuation.terms import DOSING as _ACTUATE

from orexis_agent_progression.store import bindings
from orexis_agent_progression.ontology import OREXIS, PROGRESSION

from conftest import stake_of, MOISTURE, build_agent, genesis_store, wired_markets, wired_sensors, reading_of, write_reading, predicted_reading, predicted_bands


@pytest.fixture
def thirsty(monkeypatch):
    """Fern with a fresh 0.30 on record — everything needed to bid, win, and be watched."""
    return build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)


def keeper_of(agent):
    return next(m for m in agent.modules if m.name == "intention")


def market_of(agent):
    return wired_markets(agent)[0]


def win(agent, auction="r1", amount=0.5, debit=0.2):
    """One full acquire: offer in, bid out, claim back."""
    market = market_of(agent)
    agent.deliver(market.offer_topic, {"auction_id": auction, "closes_in_s": 30})
    agent.deliver(f"{market.claim_topic}/fern", {"amount_l": amount, "debit": debit})


# --- the watch opens where the means resolves --------------------------------

def test_a_claim_opens_a_watch_with_the_baseline_in_the_row(thirsty):
    """Satisfied is the MEANS; the end gets its own record: where the property stood, which way
    the domain promises it moves, and by when. The baseline is copied into the ledger because
    the sensed graph upserts — the before of any before/after survives nowhere else."""
    win(thirsty)
    keeper = keeper_of(thirsty)
    watches = keeper.open_expectations(stake_of(thirsty).uri)
    assert len(watches) == 1
    watch = watches[0]
    assert watch.baseline == 0.30 and watch.baseline_at is not None
    assert watch.action == PRESENTING, "the watch is on the method's last step (#523)"
    assert keeper.held() == [], \
        "no shape is built per step (#639): the predictor was told the band and compares at arrival"


def test_opening_the_watch_asks_for_a_look(thirsty):
    """`sense_now` at adoption, so the freshest possible before is on record and the first
    after arrives as soon as the board can manage."""
    before = sum(1 for t, p, r in thirsty.sent if p.get("sense"))
    win(thirsty)
    assert sum(1 for t, p, r in thirsty.sent if p.get("sense")) > before


# --- the verdict: met, unmet, and never both ---------------------------------

def test_the_dose_landing_meets_the_end(thirsty):
    """The reading the step predicted, before the deadline — met, early is fine, that is the
    dose landing. The watch closes and the row now carries BOTH facts: outcome satisfied (the
    claim) and endMet true (the world answered as the search planned)."""
    win(thirsty)
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.55})
    keeper = keeper_of(thirsty)
    assert keeper.open_expectations() == []
    assert keeper.reports()["expectations_met"] == 1
    assert keeper.reports()["expectations_unmet"] == 0


def test_movement_the_wrong_way_proves_nothing_before_the_deadline(thirsty):
    """A dose may land late; drying continues meanwhile. Falling readings inside the horizon
    leave the watch open rather than judging early — unmet is a verdict about the DEADLINE."""
    win(thirsty)
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.29})
    assert len(keeper_of(thirsty).open_expectations()) == 1


def test_the_deadline_passing_unmet_is_the_false_knowledge_datum(monkeypatch):
    """The graph said this lever raises this property; the act was honoured; the property never
    moved. satisfied-and-UNMET, the signature nothing could record before #131."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)
    keeper.beliefs = replace(keeper.beliefs, patience_s=0)   # the horizon is now
    win(fern)
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.28})   # still falling
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
    assert keeper.expecting(stake_of(thirsty).uri)
    # maximum urgency earns the agent's OWN fast cadence — the floor is a clamp, not a target
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == p.beliefs.fast_sleep_s

    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.55})   # dose lands as predicted
    assert not keeper.expecting(stake_of(thirsty).uri)
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == calm


# --- the flag: suspicious after N, never auto-retracted -----------------------

def test_an_affordance_that_never_pays_becomes_suspect(monkeypatch, caplog):
    """Three acquisitions, three honoured claims, three deadlines passed with the pot still
    drying: the pair (Acquire, SoilMoisture) is flagged — a warning in the log, a line in the
    health series — and nothing is retracted, because what to do about a belief that is not
    paying is a decision, not a reflex. The agent must end up FLAGGED, not looping unmarked."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)

    value = 0.30
    with caplog.at_level(logging.WARNING):
        for auction in ("r1", "r2", "r3"):
            win(fern, auction=auction)
            value -= 0.01                                    # the world keeps refusing
            fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": round(value, 2)})
            #  The deadline passes — fired as the keeper's scheduler would (#516): the watch
            #  is a hold, and a deadline of "now" would race the reading it is meant to judge.
            for watch in keeper.open_expectations():
                keeper.lapse(watch.uri)

    assert keeper.reports()["expectations_unmet"] == 3
    assert keeper.reports()["affordances_suspect"] == 1
    assert [pair for pair in keeper.suspects()
            if pair[0] == PRESENTING and pair[1] == stake_of(fern).uri]
    assert "AFFORDANCE SUSPECT" in caplog.text


def test_one_success_resets_the_suspicion(monkeypatch):
    """Consecutive, not cumulative: an affordance that mostly pays is noisy, not false."""
    fern = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    keeper = keeper_of(fern)

    def lapse_all():
        for watch in keeper.open_expectations():
            keeper.lapse(watch.uri)

    win(fern, auction="r1")
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.29})   # not an answer
    lapse_all()                                                              # unmet
    win(fern, auction="r2")
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.40})   # met — the reset
    win(fern, auction="r3")
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.39})   # not an answer
    lapse_all()                                                              # unmet

    assert keeper.reports()["expectations_unmet"] == 2
    assert keeper.reports()["affordances_suspect"] == 0


# --- the claim waits for the watch (#132) -----------------------------------

def test_a_claim_is_held_until_the_watch_is_live(thirsty):
    """Never spend a dose you cannot watch land. The claim adopts an Apply — a held claim —
    and nothing is presented while readings arrive without the #135 stamp; the first reading
    acknowledged at the fast cadence is proof the board heard the tightening, and THAT is when
    the claim goes out, the Apply resolves, and the expectation opens with a baseline the hold
    did not age."""
    from orexis_capability_market.terms import PRESENTING

    market = market_of(thirsty)
    keeper = keeper_of(thirsty)
    #  THE ACKNOWLEDGEMENT ROAD, which is what this test is about. An alarm-armed board is
    #  a live watch the moment its thresholds go out (#151, its own test in
    #  test_subscribing), and the first reading below tightens the cadence and sends them —
    #  so with the alarm armed the claim would rightly go out there. The bidder's own check
    #  used to run before the tightening in the same hook and missed it; the keeper re-asks
    #  after every write and does not (#512). Disarmed, so the stamp is the only road.
    for sensor in thirsty.subscribing().sensors:
        object.__setattr__(sensor, "alarm", False)
    thirsty.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    thirsty.deliver(f"{market.claim_topic}/fern",
                    {"jti": "v1", "amount_l": 0.5, "debit": 0.2})

    assert thirsty.sent.to(f"{market.redeem_topic}/fern") == [], \
        "winning must present nothing — the watch is not live"
    assert len(keeper.standing(action=PRESENTING)) == 1
    assert keeper.open_expectations() == []          # the dose is not imminent yet

    # a reading arrives WITHOUT the ack — the board has not heard the tightening
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.29})
    assert thirsty.sent.to(f"{market.redeem_topic}/fern") == []

    # and one acknowledged at the fast cadence — the watch is provably live
    fast = thirsty.subscribing().beliefs.fast_sleep_s
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.29, "sleep_s": fast})
    presented = thirsty.sent.to(f"{market.redeem_topic}/fern")
    assert presented and presented[-1]["jti"] == "v1"
    assert not [p for _, _, p in keeper.held() if not p.endswith("answeredWhen")], \
        "the readiness hold is gone; the intention stands at Presenting with its watch on the end (#523)"
    watches = keeper.open_expectations(stake_of(thirsty).uri)
    assert len(watches) == 1 and watches[0].baseline == 0.29


def test_an_alarm_armed_watch_releases_the_claim_on_the_first_tightening(thirsty):
    """The other road to a live watch (#151): an alarm-armed board announces a crossing
    itself, so the watch is live the moment its thresholds have gone out. The first reading
    after the win tightens the cadence and sends them; the sensing module writes
    `sensing:watchLive true` beside the horizon; the keeper, re-asking the hold's condition
    on that write, releases Presenting there — no acknowledgement needed, and no check of
    the bidder's own. This is the behaviour the bidder's in-hook check used to miss by
    running before the tightening (#512)."""
    from orexis_capability_market.terms import PRESENTING

    market = market_of(thirsty)
    keeper = keeper_of(thirsty)
    assert all(s.alarm for s in thirsty.subscribing().sensors), "the fixture's boards are armed"
    thirsty.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    thirsty.deliver(f"{market.claim_topic}/fern",
                    {"jti": "v9", "amount_l": 0.5, "debit": 0.2})
    assert thirsty.sent.to(f"{market.redeem_topic}/fern") == [] and keeper.held(), \
        "thresholds not yet sent: held"

    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.29})
    presented = thirsty.sent.to(f"{market.redeem_topic}/fern")
    assert presented and presented[-1]["jti"] == "v9", "armed and sent: live, released, presented"
    assert not [
        h for h in keeper.held() if not h[2].endswith("answeredWhen")], \
        "the readiness hold is gone; what is held now is the watch on the dose's end"


def test_the_bounded_wait_redeems_blind_rather_than_never(thirsty):
    """Old firmware that never acks, a board mid-sleep on a long cadence — a watch that cannot
    be confirmed within one full cycle is not going to be, and a dose delayed forever is worse
    than a dose unobserved. The deadline presents the claim and says it ran blind."""
    market = market_of(thirsty)
    thirsty.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    thirsty.deliver(f"{market.claim_topic}/fern",
                    {"jti": "v2", "amount_l": 0.5, "debit": 0.2})
    assert thirsty.sent.to(f"{market.redeem_topic}/fern") == []

    #  The deadline is the KEEPER's now (#512): fire it as the scheduler would.
    from orexis_capability_market.terms import PRESENTING
    keeper = keeper_of(thirsty)
    held = keeper.standing(action=PRESENTING)
    assert len(held) == 1 and keeper.held(), "the claim stands, held until the watch is live"
    keeper.lapse(held[0].uri)
    presented = thirsty.sent.to(f"{market.redeem_topic}/fern")
    assert presented and presented[-1]["jti"] == "v2"
    assert not [
        h for h in keeper.held() if not h[2].endswith("answeredWhen")]


def test_a_held_claim_is_maximum_urgency(thirsty):
    """The hold is the watch one step earlier: the dose is coming the moment the watch is live,
    and the watch becomes live by exactly this urgency reaching the board. Claim → tight;
    presentation → the expectation takes over the same answer without a gap."""
    market = market_of(thirsty)
    p = thirsty.subscribing()
    thirsty.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 30})
    thirsty.deliver(f"{market.claim_topic}/fern",
                    {"jti": "v3", "amount_l": 0.5, "debit": 0.2})
    #  Answered by the BIDDER — it holds the claim and Apply is its word — through the same
    #  choir hook the keeper used to answer it by; the cadence below is the choir's max.
    assert thirsty.bidding().urgency(thirsty.me.acts_for, MOISTURE, 0.55) == 1.0
    assert p.cadence_for(thirsty.me.acts_for, MOISTURE, 0.55) == p.beliefs.fast_sleep_s


# --- the margin: the world answers above the grain (#165) ---------------------

def test_a_breath_of_grain_past_the_baseline_is_not_the_world_answering(thirsty):
    """The live incident, replayed: a watch was closed by +0.001 of instrument grain two
    seconds before its dose landed, and the closed watch let the same gap be bought twice
    (#167). A movement counts only when it is the one the step PREDICTED (#510): 0.5 L
    through 2.0 L-per-fraction from 0.30 is a reading of 0.55, and the bidder's tolerance
    (0.5 of the movement, the capability's default) admits 0.425–0.675. Grain clears
    nothing, and so does a reading short of the band."""
    win(thirsty)
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.301})
    keeper = keeper_of(thirsty)
    assert len(keeper.open_expectations()) == 1, "grain must not close a watch"
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.37})
    assert len(keeper.open_expectations()) == 1, "a rise short of the prediction is not it either"
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.50})
    assert keeper.open_expectations() == []
    assert keeper.reports()["expectations_met"] == 1


def test_the_step_carries_the_reading_the_rule_predicted(thirsty):
    """ONE DECLARATION (#510): the actor sizes nothing. The step the search made carries the
    reading Acquiring's own rule predicted — 0.30 plus 0.5 L through 2.0 L-per-fraction —
    and that is what the watch holds the world to."""
    win(thirsty, amount=0.5)
    watch = keeper_of(thirsty).open_expectations(stake_of(thirsty).uri)[0]
    assert [b.rsplit(".", 1)[-1] for b in predicted_bands(thirsty, watch.step)
            if "band." in b] == ["inside"], "a bought lot brings the reading into the region"


def test_a_step_that_predicts_nothing_opens_no_watch(thirsty):
    """A step the search did not make — adopted by hand, by an event — predicts nothing, and
    an expectation that cannot be judged is refused rather than left to sit unverified."""
    keeper = keeper_of(thirsty)
    uri = keeper.adopt(TENDERING, stake_of(thirsty).uri, "an act of unknowable effect")
    assert not keeper.expect(uri, "nothing predicted", baseline=reading_of(thirsty, MOISTURE))
    assert keeper.open_expectations() == []


def test_a_number_handed_in_is_held_to_the_band_it_falls_in(thirsty):
    """A caller may still state a number (#579), and the watch on a number is retired (#639):
    the world is held to the BAND the number falls in — 0.35 is below the fern's floor, as
    0.301 is, so the first reading answers — and the number stays in the residual, where the
    reviewer reads it against what the world showed."""
    keeper = keeper_of(thirsty)
    uri = keeper.adopt(TENDERING, stake_of(thirsty).uri, "an act predicting 0.35")
    assert keeper.expect(uri, "0.35, the band it falls in", baseline=reading_of(thirsty, MOISTURE),
                         predicts=predicted_reading(thirsty.me.acts_for, MOISTURE, 0.35))
    write_reading(thirsty, 0.301, MOISTURE)
    assert keeper.open_expectations() == []
    assert keeper.reports()["expectations_met"] == 1
    rows = bindings(thirsty.intentions.query_union(f"""
SELECT ?p ?o WHERE {{ <{uri}> progression:by ?s . ?s progression:predictedValue ?p ; progression:observedValue ?o }}"""))
    assert rows and float(rows[0]["p"]) == 0.35 and abs(float(rows[0]["o"]) - 0.301) < 1e-9


# --- while my own dose is unanswered, I do not buy again (#167) ---------------

def test_no_new_purchase_while_my_own_dose_is_unanswered(thirsty, caplog):
    """The double-buy, refused: the dose may have landed inside my sensor's sleep, and even a
    fresh look can race a valve that dispenses over half a minute. The bid is DECLINED, not
    gated — a judgment read off the ledger — and the world answering frees the very next round."""
    market = market_of(thirsty)
    win(thirsty)                                        # watch open, dose in flight
    bids = len(thirsty.sent.to(f"{market.bid_topic}/fern"))
    with caplog.at_level(logging.INFO, logger="fern.bidding"):
        thirsty.deliver(market.offer_topic, {"auction_id": "r2", "closes_in_s": 30})
    assert len(thirsty.sent.to(f"{market.bid_topic}/fern")) == bids, \
        "a phantom deficit was priced while my own dose was unanswered"
    assert "my own dose has not answered yet" in caplog.text

    #  THE WORLD ANSWERS by bringing the reading into the region — which is what the step
    #  predicted (#579) — so the watch closes and the guard has nothing to refuse. The plant
    #  is content at that reading and buys nothing; it is the next thirst that buys, which is
    #  what this half is about: the refusal was the open watch, not a rule against bidding.
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.50})
    assert keeper_of(thirsty).open_expectations(stake_of(thirsty).uri) == []
    #  THE NEXT THIRST BUYS AT THE READING (#632): 0.30 is outside the band the next
    #  observation was expected in, so the surprise wakes the mind at arrival, and the round
    #  still open is bid in — no further offer needed.
    thirsty.deliver(wired_sensors(thirsty)[0].reading_topic, {"moisture": 0.30})   # thirsty again
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
    fern.deliver(market.offer_topic, {"auction_id": "r2", "closes_in_s": 30})
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
    #  Both halves are the ACTOR's to pass now: the landing from its effect rule, the seeing
    #  from the sensing it holds — the keeper names neither package to find them.
    assert keeper.expect(uri, "50 seconds of pouring",
                         predicts=predicted_reading(gardener.me.acts_for, MOISTURE, 0.2),
                         lands_after_s=50.0, seeing_s=seeing,
                         baseline=reading_of(gardener, MOISTURE))

    rows = bindings(gardener.beliefs.query(f"""
SELECT ?d WHERE {{ GRAPH <{keeper.graph}> {{ <{uri}> <{PROGRESSION}by> ?act . ?act <{PROGRESSION}notAfter> ?d }} }}"""))
    window = datetime.fromisoformat(rows[0]["d"]).timestamp() - before
    assert abs(window - (50.0 + seeing)) < 2.0, (
        f"the watch should run for the dose (50s) plus how long seeing takes ({seeing}s), "
        f"and it ran for {window:.0f}s")
    assert window != pytest.approx(keeper.beliefs.patience_s, abs=2.0) or seeing + 50 == \
        keeper.beliefs.patience_s, "and not for the patience, which is a different question"


def test_an_act_that_cannot_size_itself_keeps_the_patience(monkeypatch):
    """The fallback: a caller that cannot say how long the physics takes passes nothing and
    keeps exactly the behaviour it had. A buyer is the real case — it holds
    a claim on somebody else's valve and cannot ask its own rules how long that valve stays
    open, so patience is the only honest bound it has."""
    from datetime import datetime, timezone

    gardener = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.10}, world="loner"),
                           monkeypatch)
    keeper = keeper_of(gardener)
    uri = keeper.adopt(_ACTUATE, MOISTURE, "something is on its way")
    before = datetime.now(timezone.utc).timestamp()
    assert keeper.expect(uri, "bought from someone else's valve",
                         predicts=predicted_reading(gardener.me.acts_for, MOISTURE, 0.2),
                         baseline=reading_of(gardener, MOISTURE))

    rows = bindings(gardener.beliefs.query(f"""
SELECT ?d WHERE {{ GRAPH <{keeper.graph}> {{ <{uri}> <{PROGRESSION}by> ?act . ?act <{PROGRESSION}notAfter> ?d }} }}"""))
    window = datetime.fromisoformat(rows[0]["d"]).timestamp() - before
    assert abs(window - keeper.beliefs.patience_s) < 2.0









# --- an overshoot finishes the plan (#521) -------------------------------------------------

def test_a_step_the_world_overshoots_finishes_the_plan_when_the_want_is_met(monkeypatch):
    """A two-dose plan stands. The first dose's reading comes back inside the step's
    tolerance but past the aim, and the want is met. The intention resolves SATISFIED with
    the tail finished — not advanced to a second dose an actor would size to nothing and
    leave standing until the patience ran out."""
    from orexis_agent_progression.act import Step

    gardener = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.10}, world="loner"),
                           monkeypatch)
    keeper = keeper_of(gardener)
    want = stake_of(gardener).uri
    pump = bindings(gardener.beliefs.query(
        f"SELECT ?p WHERE {{ <{gardener.me.uri}> actuation:hasActuator ?p }}"))[0]["p"]
    dose = Step(action=_ACTUATE, via=pump, want=want, about=MOISTURE, quantity=0.2)
    uri = keeper.adopt([dose, dose], want, "two doses, the search's plan")
    assert uri is not None
    assert keeper.expect(uri, "the first dose", baseline=reading_of(gardener, MOISTURE),
                         predicts=predicted_reading(
                             gardener.me.acts_for, MOISTURE,
                             band="http://example.org/orexis/sensing#InRegion"))
    finished = []
    monkeypatch.setattr(gardener, "tell",
                        lambda point, *a: finished.append(point) if point.endswith("planFinished") else None)
    write_reading(gardener, 0.20, MOISTURE)            # past the aim (0.18), inside the region
    keeper.reconsider()
    assert keeper.standing() == [], "nothing stands: the plan is finished, not waiting on a second dose"
    assert keeper.reports()["expectations_met"] == 1
    outcome = bindings(gardener.intentions.query_union(f"""
SELECT ?o ?why WHERE {{ GRAPH <{keeper.graph}> {{ <{uri}> <{PROGRESSION}outcome> ?o ; <{PROGRESSION}becauseOf> ?why }} }}"""))
    assert {r["o"] for r in outcome} == {"satisfied"}
    assert any("tail is finished" in r["why"] for r in outcome)
    assert len(keeper.walked(uri)) == 1, "one dose was taken, no second"
    assert finished, "and deliberation heard the plan finish"

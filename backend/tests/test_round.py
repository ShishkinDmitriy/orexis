"""The distributed round: announce, answer, match, issue, redeem.

A round is a conversation between processes, so these tests drive the real modules by
delivering the real messages and reading what goes back on the wire. The host and the bidder
are built separately — as they are deployed — and never share an object, which is the point:
the host cannot see a bidder's valuation, it has to ask.

Timers are exercised by calling `close()` directly, so the tests are deterministic; that the
window is *scheduled* is checked separately.
"""

from datetime import datetime, timedelta, timezone

import pytest

from conftest import build_agent, genesis_dataset


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


@pytest.fixture
def host(make):
    return make("supplier")


def market_of(agent):
    return (agent.me.hosted_markets or agent.me.markets)[0]


def offer_from(host):
    """The offer the host just announced."""
    return host.sent.to(market_of(host).offer_topic)[-1]


def low_event(agent_id="fern", value=0.05):
    return {"agent": agent_id, "subject": f"http://example.org/agora#{agent_id}",
            "value": value, "band": "LOW"}


# --- opening ---------------------------------------------------------------

def test_scarcity_opens_a_round(host):
    host.deliver("readings/fern", low_event())
    offer = offer_from(host)
    assert offer["quantity_l"] == 2.0
    assert offer["reserve_price_per_l"] == 0.20
    assert offer["closes_in_s"] == 3  # the host's own bid window
    assert offer["round_id"]


def test_a_comfortable_participant_opens_nothing(host):
    host.deliver("readings/fern", {"agent": "fern", "band": "OK", "value": 0.5})
    assert host.sent == []


def test_the_host_hears_a_verdict_not_a_moisture_reading(host):
    """It acts on the agent's own judgment; it never needs the raw number."""
    host.deliver("readings/fern", {"agent": "fern", "band": "LOW"})  # no value at all
    assert offer_from(host)["round_id"]


def test_a_flapping_participant_cannot_spam_the_market(host):
    host.deliver("readings/fern", low_event())
    first = offer_from(host)
    host.hosting().open_round = None  # the first round ended
    host.deliver("readings/tomato", low_event("tomato"))
    assert len(host.sent.to(market_of(host).offer_topic)) == 1, "cooldown should suppress it"
    assert first["round_id"]


def test_no_second_round_while_one_is_open(host):
    host.deliver("readings/fern", low_event())
    host.deliver("readings/tomato", low_event("tomato"))
    assert len(host.sent.to(market_of(host).offer_topic)) == 1


# --- answering -------------------------------------------------------------

def _with_reading(value, age_s=0):
    ts = datetime.now(timezone.utc) - timedelta(seconds=age_s)
    return genesis_dataset({"fern": value, "tomato": value, "succulent": value}, ts)


def test_a_thirsty_bidder_answers_with_its_own_number(make):
    fern = make("fern", _with_reading(0.10))
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"round_id": "r1", "closes_in_s": 3})
    bid = fern.sent.to(f"{market.bid_topic}/fern")[-1]
    assert bid["round_id"] == "r1" and bid["agent"] == "fern"
    assert bid["max_qty_l"] > 0 and bid["max_price_per_l"] > 0


def test_a_satisfied_bidder_cedes(make):
    # 0.60 is above fern's 0.55 target — a reflex, no bid
    fern = make("fern", _with_reading(0.60))
    fern.deliver(market_of(fern).offer_topic, {"round_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") == []


def test_the_same_reading_divides_them(make):
    """0.25 is parched for a fern and comfortable for a succulent."""
    fern = make("fern", _with_reading(0.25))
    succulent = make("succulent", _with_reading(0.25))
    for a in (fern, succulent):
        a.deliver(market_of(a).offer_topic, {"round_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") != []
    assert succulent.sent.under("market/") == []


def test_a_stale_reading_cannot_back_a_bid(make):
    """Bone dry, but read a day ago — owning the cadence must not mean bidding on the past."""
    fern = make("fern", _with_reading(0.05, age_s=86_400))
    fern.deliver(market_of(fern).offer_topic, {"round_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") == []


def test_each_bidder_applies_its_own_staleness_limit(make):
    """200s is past fern's 120s limit and inside the succulent's 300s."""
    fern = make("fern", _with_reading(0.05, age_s=200))
    succulent = make("succulent", _with_reading(0.05, age_s=200))
    for a in (fern, succulent):
        a.deliver(market_of(a).offer_topic, {"round_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") == []
    assert succulent.sent.under("market/") != []


# --- look before you bid ---------------------------------------------------

def test_the_bidder_asks_its_sensor_and_waits(make):
    """With nothing in hand it must not answer from stale storage — it looks first."""
    fern = make("fern")  # no readings at all
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"round_id": "r1", "closes_in_s": 3})

    sensor = fern.me.sensors[0]
    assert {"sense": True} in fern.sent.to(sensor.command_topic), "it should nudge its board"
    assert fern.sent.under(market.bid_topic) == [], "and not bid before the answer arrives"

    fern.deliver(sensor.reading_topic, {"value": 0.10})  # the board answers
    bid = fern.sent.to(f"{market.bid_topic}/fern")[-1]
    assert bid["round_id"] == "r1"


def test_a_silent_sensor_means_sitting_the_round_out(make):
    fern = make("fern")
    fern.deliver(market_of(fern).offer_topic, {"round_id": "r1", "closes_in_s": 3})
    fern.bidding().give_up()  # the window closed with no answer
    assert fern.sent.under(market_of(fern).bid_topic) == []


def test_a_late_reading_does_not_bid_into_a_closed_round(make):
    fern = make("fern")
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"round_id": "r1", "closes_in_s": 3})
    fern.bidding().give_up()
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.10})
    assert fern.sent.under(market.bid_topic) == []


# --- collecting ------------------------------------------------------------

def a_bid(agent="fern", round_id=None, qty=1.0, price=0.5, balance=100.0):
    return {"round_id": round_id, "agent": agent, "max_qty_l": qty,
            "max_price_per_l": price, "balance": balance}


def open_round(host):
    host.deliver("readings/fern", low_event())
    return offer_from(host)["round_id"]


def test_a_bid_from_a_stranger_is_ignored(host):
    rid = open_round(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/orchid", a_bid("orchid", rid))
    assert host.hosting().open_round["bids"] == {}


def test_a_bid_for_another_round_is_ignored(host):
    open_round(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", "some-other-round"))
    assert host.hosting().open_round["bids"] == {}


def test_bids_are_collected_until_the_window_closes(host):
    rid = open_round(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid))
    host.deliver(f"{market.bid_topic}/tomato", a_bid("tomato", rid))
    assert set(host.hosting().open_round["bids"]) == {"fern", "tomato"}


# --- closing ---------------------------------------------------------------

def test_a_round_with_no_bids_issues_nothing(host):
    open_round(host)
    host.hosting().close()
    assert host.sent.under(market_of(host).voucher_topic) == []


def test_nothing_below_the_reserve_clears(host):
    rid = open_round(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, price=0.01))  # reserve is 0.20
    host.hosting().close()
    assert host.sent.under(market.voucher_topic) == []


def test_the_winner_gets_a_voucher_on_its_own_channel(host):
    rid = open_round(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, qty=0.5, price=0.6))
    host.hosting().close()
    voucher = host.sent.to(f"{market.voucher_topic}/fern")[-1]
    assert voucher["sub"] == "fern" and voucher["amount_l"] > 0
    assert voucher["jti"] and voucher["round_id"] == rid


def test_the_higher_bid_is_served_first(host):
    rid = open_round(host)
    market = market_of(host)
    # 2.0 L on offer; tomato wants all of it but bids less
    host.deliver(f"{market.bid_topic}/tomato", a_bid("tomato", rid, qty=2.0, price=0.3))
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, qty=2.0, price=0.9))
    host.hosting().close()
    assert host.sent.to(f"{market.voucher_topic}/fern")[-1]["amount_l"] == 2.0
    assert host.sent.to(f"{market.voucher_topic}/tomato") == []


def test_the_supply_is_never_oversold(host):
    rid = open_round(host)
    market = market_of(host)
    for who in ("fern", "tomato", "succulent"):
        host.deliver(f"{market.bid_topic}/{who}", a_bid(who, rid, qty=5.0, price=0.9))
    host.hosting().close()
    total = sum(v["amount_l"] for v in host.sent.under(market.voucher_topic))
    assert total <= 2.0 + 1e-9


def _win_for_fern(host):
    rid = open_round(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, qty=0.5, price=0.6))
    host.hosting().close()
    return host.me.actuator_for("fern")


def test_winning_opens_the_valve(host):
    host.module("actuation").armed = True  # a pump is wired and calibrated
    valve = _win_for_fern(host)
    command = host.sent.to(valve.command_topic)[-1]
    assert command["ml"] > 0 and command["seconds"] > 0
    assert command["plant"] == "fern"
    assert command["match_sig"] and command["val_sig"]  # co-signed, or the device refuses


def test_a_disarmed_host_still_clears_but_waters_nothing(host):
    """The sensor-only phase: decide, issue, log — and touch no hardware."""
    host.module("actuation").armed = False
    valve = _win_for_fern(host)
    assert host.sent.to(f"{market_of(host).voucher_topic}/fern") != []  # the round completed
    assert host.sent.to(valve.command_topic) == []  # but no valve moved


# --- what comes back -------------------------------------------------------

def test_the_winner_debits_its_own_wallet(make):
    fern = make("fern", _with_reading(0.10))
    market = market_of(fern)
    before = fern.bidding().balance
    fern.deliver(f"{market.voucher_topic}/fern",
                 {"round_id": "r1", "amount_l": 0.5, "debit": 0.30})
    assert fern.bidding().balance == pytest.approx(before - 0.30)
    assert fern.bidding().won_l == 0.5


# --- the window is real ----------------------------------------------------

def test_the_host_schedules_the_close(host):
    """The round must end on its own; nothing else would close it."""
    open_round(host)
    timer = host.hosting()._timer
    assert timer is not None and timer.interval_s == host.hosting().beliefs.bid_window_s
    timer.stop()


def test_the_bidder_gives_up_when_the_window_passes(make):
    fern = make("fern")
    fern.deliver(market_of(fern).offer_topic, {"round_id": "r1", "closes_in_s": 3})
    deadline = fern.bidding()._deadline
    assert deadline is not None and deadline.interval_s == 3
    deadline.stop()

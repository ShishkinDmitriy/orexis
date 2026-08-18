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

from conftest import HUMIDITY, MOISTURE, build_agent, genesis_store


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


@pytest.fixture
def host(make, tmp_path, monkeypatch):
    """The supplier, with signing keys it mints for itself.

    It used to read `world/society/secrets/`, which is gitignored — so this passed only on a
    machine that happened to have keys lying there, and could not pass in a fresh clone. CI found
    that on its first run, after two agents had reported it and I had called it environmental.
    A test that depends on a secret nobody can commit has to make its own.
    """
    from onboarding.keygen import create_keypair

    monkeypatch.setenv("AGORA_WORLD_DIR", str(tmp_path))
    (tmp_path / "secrets").mkdir()
    for name in ("host", "clearing"):
        create_keypair(name)
    return make("supplier")


def market_of(agent):
    return (agent.me.hosted_markets or agent.me.markets)[0]


def offer_from(host):
    """The offer the host just announced."""
    return host.sent.to(market_of(host).offer_topic)[-1]


def low_event(agent_id="fern", value=0.05, observed_property=MOISTURE):
    """What a participant actually publishes when it is in trouble.

    The property is not decoration and is not optional: an agent may hold a desire in several
    properties now, so it announces several verdicts, and a host that took any LOW band it was
    sent would open a water auction because somebody's greenhouse got cold. `agent/observation.py`
    has named the property since a subject with two sensors started announcing two values on one
    topic; the host reads it.
    """
    return {"agent": agent_id, "subject": f"http://example.org/agora#{agent_id}",
            "property": observed_property, "value": value, "band": "LOW"}


# --- opening ---------------------------------------------------------------

def test_scarcity_opens_a_round(host):
    host.deliver("readings/fern", low_event())
    offer = offer_from(host)
    assert offer["quantity_l"] == 2.0
    assert offer["reserve_price_per_l"] == 0.20
    assert offer["closes_in_s"] == 3  # the host's own bid window
    assert offer["auction_id"]


def test_the_offer_announces_the_rule_bidders_are_bidding_under(host):
    """Terms travel with the invitation, as a real auction announces them when it opens.

    A bidder cannot bid well against terms it does not know: under pay-as-bid a winner pays
    what it offered, so the honest strategy is to shade, and under a uniform price it is not.
    Read off the provider rather than a belief, so what is announced is necessarily what runs —
    a host cannot advertise one rule and apply another.
    """
    from packages.capability.market import PAY_AS_BID

    host.deliver("readings/fern", low_event())
    assert offer_from(host)["matches_by"] == PAY_AS_BID
    assert host.hosting().matcher().CAPABILITY == PAY_AS_BID


def test_a_comfortable_participant_opens_nothing(host):
    host.deliver("readings/fern", {"agent": "fern", "band": "OK", "value": 0.5})
    assert host.sent == []


def test_the_host_hears_a_verdict_not_a_moisture_reading(host):
    """It acts on the agent's own judgment; it never needs the raw number.

    The property stays — that is not the number, it is which scale the verdict is on, and a host
    that cannot tell moisture from humidity would open a round on either.
    """
    host.deliver("readings/fern",
                 {"agent": "fern", "property": MOISTURE, "band": "LOW"})  # no value at all
    assert offer_from(host)["auction_id"]


def test_a_flapping_participant_cannot_spam_the_market(host):
    host.deliver("readings/fern", low_event())
    first = offer_from(host)
    host.hosting().open_auction = None  # the first round ended
    host.deliver("readings/tomato", low_event("tomato"))
    assert len(host.sent.to(market_of(host).offer_topic)) == 1, "cooldown should suppress it"
    assert first["auction_id"]


def test_trouble_in_a_property_this_market_cannot_relieve_opens_nothing(host):
    """A defect that became reachable the moment an agent could want more than one thing.

    Nothing relieves a cold night by dispensing water, so a round opened on that band would spend
    a real allocation on a reading it cannot act on — and it would have, because the host took
    any `band == "LOW"` it was sent. It had never been wrong before only because exactly one
    module annotated exactly one property.

    The filter asks the DOMAIN what a bid is priced in, never the market: a market is a lot, and
    `market:aboutProperty` refuses to hang a property off one.
    """
    host.deliver("readings/fern", low_event(observed_property=HUMIDITY))
    assert not host.sent.to(market_of(host).offer_topic)

    host.deliver("readings/fern", low_event())
    assert len(host.sent.to(market_of(host).offer_topic)) == 1


def test_no_second_round_while_one_is_open(host):
    host.deliver("readings/fern", low_event())
    host.deliver("readings/tomato", low_event("tomato"))
    assert len(host.sent.to(market_of(host).offer_topic)) == 1


# --- answering -------------------------------------------------------------

def _with_reading(value, age_s=0):
    ts = datetime.now(timezone.utc) - timedelta(seconds=age_s)
    return genesis_store({"fern": value, "tomato": value, "succulent": value}, ts)


def test_a_thirsty_bidder_answers_with_its_own_number(make):
    fern = make("fern", _with_reading(0.10))
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    bid = fern.sent.to(f"{market.bid_topic}/fern")[-1]
    assert bid["auction_id"] == "r1" and bid["agent"] == "fern"
    assert bid["max_qty_l"] > 0 and bid["max_price_per_l"] > 0


def test_a_satisfied_bidder_cedes(make):
    # 0.60 is above fern's 0.55 target — a reflex, no bid
    fern = make("fern", _with_reading(0.60))
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") == []


def test_the_same_reading_divides_them(make):
    """0.25 is parched for a fern and comfortable for a succulent."""
    fern = make("fern", _with_reading(0.25))
    succulent = make("succulent", _with_reading(0.25))
    for a in (fern, succulent):
        a.deliver(market_of(a).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") != []
    assert succulent.sent.under("market/") == []


def test_a_stale_reading_cannot_back_a_bid(make):
    """Bone dry, but read a day ago — owning the cadence must not mean bidding on the past."""
    fern = make("fern", _with_reading(0.05, age_s=86_400))
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") == []


def test_staleness_is_measured_against_the_cadence_the_agent_asked_for(make):
    """A reading that arrived when the agent asked for it is not stale, however old.

    The limit used to be absolute, which meant an agent that let a comfortable board sleep for
    600s then refused every reading older than 120s — contradicting its own instruction and
    reporting it as a failed sensor. It is now the interval in force plus a grace.

    Nothing has aimed this agent yet, so the interval in force is the slowest it would ask for.
    """
    fern = make("fern", _with_reading(0.05, age_s=200))
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") != [], (
        "200s is well inside slowSleepS + grace, so this reading arrived as instructed")


def test_sitting_out_says_which_of_three_things_happened(make):
    """Content, ignorant and broken were reported identically, so a real failure read as routine.

    Not a test of wording — of the distinction. If these three collapse to one string again, a
    quiet sensor becomes indistinguishable from a board sleeping exactly as instructed.
    """
    from packages.capability.market.terms import BIDDING

    def why(agent):
        bidding = next(m for m in agent.modules if m.CAPABILITY == BIDDING)
        return bidding._why_blind()

    never = why(make("fern"))
    asleep = why(make("fern", _with_reading(0.5, age_s=10)))
    quiet = why(make("fern", _with_reading(0.5, age_s=6_000)))

    assert "no reading yet" in never
    assert "asleep" in asleep
    assert "gone quiet" in quiet
    assert len({never, asleep, quiet}) == 3, "three states must not collapse into one message"


def test_a_bidder_waiting_for_a_reading_ignores_one_of_another_property(make):
    """The harm, at the place it would have been done: buying water because the AIR was dry.

    A bidder that has asked its sensor and is waiting used to answer on the first reading of
    its subject to arrive, whatever it was about. On a pot with a moisture probe and the
    temp/humidity board that is a race.

    The property used here is humidity rather than temperature, deliberately. Both are wrong,
    but they fail differently, and only one of them costs money: 21.0 read as a moisture
    fraction is far above any target, so the agent simply cedes and loses the round quietly.
    0.10 read as a moisture fraction is a parched plant — a plausible, actionable number in the
    wrong unit, which is exactly what the market cannot detect, because a bid is private and
    this one is perfectly well-formed.
    """
    from packages.capability.market.terms import BIDDING

    fern = make("fern")  # nothing in hand, so it waits
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    bidding = next(m for m in fern.modules if m.CAPABILITY == BIDDING)

    bidding.on_reading_recorded(fern.me.acts_for, HUMIDITY, 0.10)
    assert fern.sent.under("market/") == [], "dry air is not a reason to buy water"

    bidding.on_reading_recorded(fern.me.acts_for, MOISTURE, 0.10)
    assert fern.sent.under("market/") != [], "the reading it was actually waiting for"


def test_a_bidder_whose_domain_prices_no_property_refuses_to_start(make):
    """The link is asked of the DOMAIN's valuation term, not of the market, so this is what its
    absence breaks.

    A market is a lot — 1L of water is 1L of water whether or not anyone's soil is dry, and a
    market for something no instrument measures must stay expressible. The valuation is the
    property-shaped thing: litres per fraction OF something. With that unsaid the only
    remaining rule is "judge whichever reading arrived last", which is the defect, so the agent
    declines to run instead.
    """
    from agent.ontology import ONTOLOGY_GRAPH

    ds = genesis_store()
    ds.update(f"""DELETE WHERE {{ GRAPH <{ONTOLOGY_GRAPH}> {{
        <http://example.org/agora/water#litresPerFraction>
        <http://example.org/agora/market#aboutProperty> ?p }} }}""")

    with pytest.raises(RuntimeError, match="aboutProperty"):
        make("fern", ds)


def test_a_reading_past_the_cadence_and_its_grace_is_stale(make):
    """The rule still bites — it is relative, not absent."""
    fern = make("fern", _with_reading(0.05, age_s=6_000))
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    assert fern.sent.under("market/") == []


# --- look before you bid ---------------------------------------------------

def test_the_bidder_asks_its_sensor_and_waits(make):
    """With nothing in hand it must not answer from stale storage — it looks first."""
    fern = make("fern")  # no readings at all
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})

    sensor = fern.me.sensors[0]
    assert {"sense": True} in fern.sent.to(sensor.command_topic), "it should nudge its board"
    assert fern.sent.under(market.bid_topic) == [], "and not bid before the answer arrives"

    fern.deliver(sensor.reading_topic, {"moisture": 0.10})  # the board answers
    bid = fern.sent.to(f"{market.bid_topic}/fern")[-1]
    assert bid["auction_id"] == "r1"


def test_a_silent_sensor_means_sitting_the_round_out(make):
    fern = make("fern")
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    fern.bidding().give_up()  # the window closed with no answer
    assert fern.sent.under(market_of(fern).bid_topic) == []


def test_a_late_reading_does_not_bid_into_a_closed_round(make):
    fern = make("fern")
    market = market_of(fern)
    fern.deliver(market.offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    fern.bidding().give_up()
    fern.deliver(fern.me.sensors[0].reading_topic, {"moisture": 0.10})
    assert fern.sent.under(market.bid_topic) == []


# --- collecting ------------------------------------------------------------

def a_bid(agent="fern", auction_id=None, qty=1.0, price=0.5, balance=100.0):
    return {"auction_id": auction_id, "agent": agent, "max_qty_l": qty,
            "max_price_per_l": price, "balance": balance}


def open_auction(host):
    host.deliver("readings/fern", low_event())
    return offer_from(host)["auction_id"]


def test_a_bid_from_a_stranger_is_ignored(host):
    rid = open_auction(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/orchid", a_bid("orchid", rid))
    assert host.hosting().open_auction["bids"] == {}


def test_a_bid_for_another_round_is_ignored(host):
    open_auction(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", "some-other-round"))
    assert host.hosting().open_auction["bids"] == {}


def test_bids_are_collected_until_the_window_closes(host):
    rid = open_auction(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid))
    host.deliver(f"{market.bid_topic}/tomato", a_bid("tomato", rid))
    assert set(host.hosting().open_auction["bids"]) == {"fern", "tomato"}


# --- closing ---------------------------------------------------------------

def test_a_round_with_no_bids_issues_nothing(host):
    open_auction(host)
    host.hosting().close()
    assert host.sent.under(market_of(host).claim_topic) == []


def test_nothing_below_the_reserve_clears(host):
    rid = open_auction(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, price=0.01))  # reserve is 0.20
    host.hosting().close()
    assert host.sent.under(market.claim_topic) == []


def test_the_winner_gets_a_claim_on_its_own_channel(host):
    rid = open_auction(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, qty=0.5, price=0.6))
    host.hosting().close()
    claim = host.sent.to(f"{market.claim_topic}/fern")[-1]
    assert claim["sub"] == "fern" and claim["amount_l"] > 0
    assert claim["jti"] and claim["auction_id"] == rid


def test_the_higher_bid_is_served_first(host):
    rid = open_auction(host)
    market = market_of(host)
    # 2.0 L on offer; tomato wants all of it but bids less
    host.deliver(f"{market.bid_topic}/tomato", a_bid("tomato", rid, qty=2.0, price=0.3))
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, qty=2.0, price=0.9))
    host.hosting().close()
    assert host.sent.to(f"{market.claim_topic}/fern")[-1]["amount_l"] == 2.0
    assert host.sent.to(f"{market.claim_topic}/tomato") == []


def test_the_supply_is_never_oversold(host):
    rid = open_auction(host)
    market = market_of(host)
    for who in ("fern", "tomato", "succulent"):
        host.deliver(f"{market.bid_topic}/{who}", a_bid(who, rid, qty=5.0, price=0.9))
    host.hosting().close()
    total = sum(v["amount_l"] for v in host.sent.under(market.claim_topic))
    assert total <= 2.0 + 1e-9


def _win_for_fern(host):
    rid = open_auction(host)
    market = market_of(host)
    host.deliver(f"{market.bid_topic}/fern", a_bid("fern", rid, qty=0.5, price=0.6))
    host.hosting().close()
    return host.me.actuator_for("fern")


def test_winning_issues_paper_and_only_presenting_opens_the_valve(host):
    """Winning is not actuating (#132). The host used to redeem every claim itself the moment
    it issued them — spending the dose before the winner's sensor could possibly be watching it
    land. The claim is HELD now: no valve moves at the win, and the holder presenting it on the
    redeem channel is what actuates, co-signed exactly as before."""
    valve = _win_for_fern(host)
    assert host.sent.to(valve.command_topic) == [], \
        "the win itself must move no water — the holder has not presented"

    market = market_of(host)
    claim = host.sent.to(f"{market.claim_topic}/fern")[-1]
    host.deliver(f"{market.redeem_topic}/fern", {"jti": claim["jti"], "sub": "fern"})
    command = host.sent.to(valve.command_topic)[-1]
    assert command["ml"] > 0 and command["seconds"] > 0
    assert command["plant"] == "fern"
    assert command["match_sig"] and command["val_sig"]  # co-signed, or the device refuses


def test_a_claim_is_single_use(host):
    """Presented twice, honoured once — jti is the anti-replay id doing its job."""
    valve = _win_for_fern(host)
    market = market_of(host)
    claim = host.sent.to(f"{market.claim_topic}/fern")[-1]
    host.deliver(f"{market.redeem_topic}/fern", {"jti": claim["jti"], "sub": "fern"})
    host.deliver(f"{market.redeem_topic}/fern", {"jti": claim["jti"], "sub": "fern"})
    assert len(host.sent.to(valve.command_topic)) == 1


def test_nobody_spends_another_agents_claim(host):
    """The presenter is read off the topic the ACL lets it write — tomato cannot present
    fern's jti from its own segment, and a forged claim earns a log line, not water."""
    valve = _win_for_fern(host)
    market = market_of(host)
    claim = host.sent.to(f"{market.claim_topic}/fern")[-1]
    host.deliver(f"{market.redeem_topic}/tomato", {"jti": claim["jti"], "sub": "tomato"})
    assert host.sent.to(valve.command_topic) == []


def test_an_unknown_claim_moves_nothing(host):
    valve = _win_for_fern(host)
    market = market_of(host)
    host.deliver(f"{market.redeem_topic}/fern", {"jti": "forged", "sub": "fern"})
    assert host.sent.to(valve.command_topic) == []


# --- what comes back -------------------------------------------------------

def test_the_winner_debits_its_own_wallet(make):
    fern = make("fern", _with_reading(0.10))
    market = market_of(fern)
    before = fern.bidding().balance
    fern.deliver(f"{market.claim_topic}/fern",
                 {"auction_id": "r1", "amount_l": 0.5, "debit": 0.30})
    assert fern.bidding().balance == pytest.approx(before - 0.30)
    assert fern.bidding().won_l == 0.5


# --- the window is real ----------------------------------------------------

def test_the_host_schedules_the_close(host):
    """The round must end on its own; nothing else would close it."""
    open_auction(host)
    timer = host.hosting()._timer
    assert timer is not None and timer.interval_s == host.hosting().beliefs.bid_window_s
    timer.stop()


def test_the_bidder_gives_up_when_the_window_passes(make):
    fern = make("fern")
    fern.deliver(market_of(fern).offer_topic, {"auction_id": "r1", "closes_in_s": 3})
    deadline = fern.bidding()._deadline
    assert deadline is not None and deadline.interval_s == 3
    deadline.stop()


def test_a_host_that_states_uniform_price_runs_it_and_says_so(make, tmp_path, monkeypatch):
    """The slot, demonstrated rather than asserted.

    Everything between a world stating `market:UniformPrice` and a bidder being billed at the
    clearing price is machinery that already existed: the derivation grants whichever rule the
    host names, the loader registers whichever module declares it, and `provider` hands it over
    without the market package knowing either exists. Adding the second member moved nothing but
    its own package — this is what checks that.

    Built from a real world directory rather than by editing the graph, because the point is the
    DERIVATION: patching `market:matchesBy` after `refresh_public` has run leaves the capability the
    rules already computed, and the test would pass while proving nothing.
    """
    import shutil

    from onboarding.keygen import create_keypair

    from agent import genesis
    from packages.capability.market import UNIFORM_PRICE
    from agent.genesis import agent_id_of
    from agent.store import Store

    world = tmp_path / "world"
    shutil.copytree(genesis.world_dir("simulation"), world, dirs_exist_ok=True)
    (world / "secrets").mkdir(exist_ok=True)
    # The one edit a sovereign makes: this host runs a different auction.
    ttl = world / "world.ttl"
    ttl.write_text(ttl.read_text().replace("market:matchesBy market:PayAsBid", "market:matchesBy market:UniformPrice"))

    monkeypatch.setenv("AGORA_WORLD_DIR", str(world))
    for name in ("host", "clearing"):
        create_keypair(name)

    store = Store()
    genesis.refresh_public(store, world)
    for beliefs in sorted(world.glob(genesis.BELIEFS_GLOB)):
        genesis.birth(store, world, agent_id_of(beliefs))
    host = make("supplier", store)

    assert host.hosting().matcher().CAPABILITY == UNIFORM_PRICE
    host.deliver("readings/fern", low_event())
    assert offer_from(host)["matches_by"] == UNIFORM_PRICE


# --- the dealer's redemption (#201 aftermath) -------------------------------

def test_a_winner_named_unlike_its_subject_still_gets_its_dose(make, tmp_path, monkeypatch):
    """The city redeeming for the supplier: the claim names the buying AGENT, and the dose
    goes to what it ACTS FOR. `actuator_for(claim.sub)` worked for every claim ever redeemed
    because a pot and its agent share a localId (fern's pot is "fern") — an id coincidence
    standing in for a one-triple walk, and the first buyer named unlike its subject broke it
    live: the dealer is "supplier", its barrel is "barrel1", and the city owned a perfectly
    good valve it could not find while the barrel sat at 0.000."""
    from onboarding.keygen import create_keypair

    from agent.clearing import Claim

    monkeypatch.setenv("AGORA_WORLD_DIR", str(tmp_path))
    (tmp_path / "secrets").mkdir()
    for name in ("host", "clearing"):
        create_keypair(name)
    city = make("city")
    actuation = next(m for m in city.modules if m.name == "actuation")
    cmd, device = actuation.command_for(
        Claim(jti="j1", sub="supplier", amount_l=2.0, debit=0.3, scope="water", auction_id="a1"))
    assert device.local_id == "city_valve", (
        "the winner's subject, found through actsFor — never the winner's own name")
    assert cmd.ml == 2000.0


# --- the host and its vessel (arc 5: no phantom water) ----------------------

def stock_reading(host, litres):
    """The barrel's level arriving as it really does — through the wire and the listener."""
    host.deliver("sensors/barrel1_level/reading", {"value": litres})


def test_a_round_is_sized_by_the_vessel_not_the_belief(host):
    """The lot is the host's standing offer; the vessel is physics. Live on the bench, a
    barrel at 0.000 kept selling 2 L lots and the sim valve poured water from nothing —
    conservation violated while every module behaved exactly as written. A host with a
    witness on its source now offers min(lot, stock)."""
    stock_reading(host, 1.5)
    host.deliver("readings/fern", low_event())
    assert offer_from(host)["quantity_l"] == 1.5


def test_a_dry_vessel_defers_the_round_until_the_refill_lands(host):
    """The two-step, held by the market: a LOW nobody can serve is not sold phantom water —
    the round is DEFERRED, and the moment the host's own witness reports the refill, the
    round it owed opens, cooldown respected. Acquire upstream, then offer: the planning
    record's first honest customer, distributed across the dealer's two venues."""
    stock_reading(host, 0.0)
    host.deliver("readings/fern", low_event())
    assert host.sent.to(market_of(host).offer_topic) == [], \
        "a dry vessel must not announce a lot it cannot pour"

    stock_reading(host, 2.5)  # the refill lands — step two opens by itself
    offer = offer_from(host)
    assert offer["quantity_l"] == 2.0, "full lot again — the belief is the cap, stock permitting"


def test_a_blind_host_sells_as_it_always_did(make, tmp_path, monkeypatch):
    """The city has no witness on its mains — honestly: the pressure is always there, and
    1000 L is a constitutional ceiling, not a stock anyone watches. A host without a witness
    keeps the old behaviour unchanged, which is what keeps this a widening."""
    from onboarding.keygen import create_keypair

    monkeypatch.setenv("AGORA_WORLD_DIR", str(tmp_path))
    (tmp_path / "secrets").mkdir()
    for name in ("host", "clearing"):
        create_keypair(name)
    city = make("city")
    city.deliver("readings/supplier", low_event(
        agent_id="supplier", observed_property=STORED))
    offers = city.sent.to("market/city_mains/offer")
    assert len(offers) == 1 and offers[0]["quantity_l"] == 3.0


STORED = "http://example.org/agora/water#StoredLitres"


# --- the owed round is a commitment the ledger sees (#206) ------------------

def keeper_of(agent):
    return next(m for m in agent.modules if m.name == "intention")


def test_a_deferred_round_stands_in_the_ledger_and_resolves_on_the_refill(host):
    """The 'host keeps no gap ledger' line, crossed knowingly: a deferral held only in module
    memory was a promise a restart forgot and no ask could see. Deciding is still nobody's —
    physics deferred the round — but OWING it is a commitment, and commitments are ledgered:
    adopted with the trigger's name when the vessel is dry, satisfied when the refill lands
    and the round opens."""
    stock_reading(host, 0.0)
    host.deliver("readings/fern", low_event())
    owed = [s for s in keeper_of(host).standing() if s.means.endswith("Offer")]
    assert len(owed) == 1 and owed[0].observed_property == STORED, \
        "the owed round stands, keyed by the stock that gates it"

    stock_reading(host, 2.5)
    assert not [s for s in keeper_of(host).standing() if s.means.endswith("Offer")], \
        "the refill landed, the round opened, the debt is paid"
    assert offer_from(host)["quantity_l"] == 2.0


def test_an_owed_round_survives_the_process_that_owed_it(host, make):
    """The whole point of the crossing: the deferral is recovered FROM the ledger at start,
    so a restarted host still owes what it owed — the round reopens on the next stock
    reading exactly as it would have, and no phantom water is sold meanwhile."""
    stock_reading(host, 0.0)
    host.deliver("readings/fern", low_event())
    assert [s for s in keeper_of(host).standing() if s.means.endswith("Offer")]

    reborn = make("supplier", host.store)  # same store: the volume the ledger lives in
    assert reborn.sent.to(market_of(reborn).offer_topic) == []
    stock_reading(reborn, 3.0)
    assert offer_from(reborn)["quantity_l"] == 2.0, \
        "the recovered debt opened the round the moment the vessel could pour"

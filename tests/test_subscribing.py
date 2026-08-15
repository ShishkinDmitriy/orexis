"""sensing:Subscribing — attention as the agent's own decision, bounded by the constitution.

The agent states an interval and the device keeps to it. What is the agent's here is the
*policy* — how often to look, and how that moves with trouble; what it delegates is only the
timekeeping. Driven through a real agent, so the numbers come from the agent's own beliefs and
the bounds from the ontology — neither is written down here.
"""

import logging
from dataclasses import replace

import pytest

from conftest import HUMIDITY, MOISTURE, TEMPERATURE, build_agent, genesis_store


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_store(), monkeypatch)


def sensor_of(agent):
    return agent.me.sensors[0]


def cadence_for(agent, value, observed_property=MOISTURE):
    """The cadence the agent would choose for a reading of its own subject.

    Three arguments now, and deliberately: sensing asks about a *property of* a subject,
    because whether a number is trouble is the stakeholder's answer, and a stake is held in
    one property. A thermometer's reading of the same pot is not the bidder's business.
    """
    return agent.subscribing().cadence_for(agent.me.acts_for, observed_property, value)


def cadences(agent):
    """Every cadence the agent has commanded, in order."""
    return [p["sleep_s"] for p in agent.sent.to(sensor_of(agent).command_topic)
            if "sleep_s" in p]


# --- the policy ------------------------------------------------------------

def test_it_watches_closely_at_the_edge_of_what_its_plant_survives(fern):
    """Its fastest at the survival floor, its slowest at the point of its region.

    Both ends moved when desire started deducing the region, and the move is the policy rather
    than a rescaling. The scale used to run from the agent's own low band to its own high band,
    so *soaked* was the most comfortable reading there is; it now runs from the middle of where
    the plant does well out to where the plant dies, on each side separately. Fern's world says
    0.45-0.65 with survival 0.20-0.85.
    """
    assert cadence_for(fern, 0.20) == 30    # the survival floor -> its fastest
    assert cadence_for(fern, 0.55) == 600   # the point of its region -> its slowest


def test_too_wet_is_trouble_too(fern):
    """The old scale had nothing above the high band, so a drowning plant read as the most
    comfortable plant there is. Attention now rises on both sides, at the rate each side's own
    survival room implies — which for this fern is gentler upward than downward, because it has
    0.20 of room above its region and 0.25 below its centre."""
    assert cadence_for(fern, 0.85) == 30     # the survival ceiling -> its fastest
    assert cadence_for(fern, 0.70) < 600     # past the region and already worth a look


def test_attention_scales_with_trouble(fern):
    assert cadence_for(fern, 0.40) < cadence_for(fern, 0.60)


def test_attention_without_a_stake_falls_back_to_the_slow_cadence(fern):
    """Urgency is supplied by whoever holds a band. Asked about a subject it has no stake in,
    the agent has no opinion — and an agent with no opinion does not watch closely."""
    p = fern.subscribing()
    assert p.cadence_for("http://example.org/agora#someone_elses_plant", MOISTURE, 0.0) == \
        p.beliefs.slow_sleep_s


def test_a_property_it_has_no_stake_in_gets_no_verdict(fern):
    """Its own pot — but a humidity, and this fern's plant states no humidity range.

    The distinction that matters is *no opinion* versus *an opinion of zero*, which is why this
    tests for None rather than for a cadence. 0.46 read as a moisture fraction lands just inside
    the region and so scores as almost perfectly comfortable: the wrong answer and a plausible
    number, which is the worst way for a bug to present. An assertion about the resulting cadence
    passes whether or not the property is checked, and one about urgency does not.

    It used to be asked about a TEMPERATURE, which fern does poll and now genuinely wants — its
    plant states an air-temperature range as well as a moisture one, which is the whole of what
    "an agent may want more than one thing" bought. Humidity is the property nothing in this
    world has an opinion about.
    """
    assert fern.urgency(fern.me.acts_for, HUMIDITY, 0.46) is None
    assert fern.annotations(fern.me.acts_for, HUMIDITY, 0.46) == {}

    assert fern.urgency(fern.me.acts_for, MOISTURE, 0.10) is not None
    assert fern.annotations(fern.me.acts_for, MOISTURE, 0.10) == {"band": "LOW"}


def test_it_holds_an_opinion_about_every_property_its_plant_states_a_range_for(fern):
    """The seam #110 recorded, closed and visible: two desires, in two units, one agent.

    Nothing bids on air temperature — no market relieves it — and a cold snap still makes this
    agent watch its board more closely. That is the cheapest slice the issue asked for, and it
    needed no market to exist.
    """
    assert fern.annotations(fern.me.acts_for, TEMPERATURE, 21.0) == {"band": "OK"}
    assert fern.annotations(fern.me.acts_for, TEMPERATURE, 6.0) == {"band": "LOW"}
    assert fern.urgency(fern.me.acts_for, TEMPERATURE, 5.0) == 1.0
    assert fern.urgency(fern.me.acts_for, TEMPERATURE, 21.0) == 0.0


def test_the_bounds_come_from_the_ontology_not_the_code(fern):
    """MIN/MAX are stated in capabilities/sensing/ontology.ttl and read at startup."""
    p = fern.subscribing()
    assert (p.min_sleep_s, p.max_sleep_s) == (10, 900)


def test_no_agent_can_exceed_the_constitutional_ceiling(fern):
    """Even an agent that wants to nap forever is clamped — the shapes reject such beliefs
    too, so this is the second of three independent guards (the third is the firmware)."""
    p = fern.subscribing()
    p.beliefs = replace(p.beliefs, slow_sleep_s=99_999)
    # The point of its region, which is the only reading that asks for the slow cadence in full.
    # It used to be 0.99 — a number chosen when anything above the high band scored as perfectly
    # comfortable, and which now correctly asks for the fastest cadence there is.
    assert cadence_for(fern, 0.55) == p.max_sleep_s


def test_no_agent_can_hammer_its_sensor_flat(fern):
    p = fern.subscribing()
    p.beliefs = replace(p.beliefs, fast_sleep_s=1)
    assert cadence_for(fern, 0.0) == p.min_sleep_s


# --- the two levers --------------------------------------------------------

def test_cadence_is_retained_so_a_sleeping_board_gets_it(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.2})
    retained = [r for t, p, r in fern.sent
                if t == sensor_of(fern).command_topic and "sleep_s" in p]
    assert retained and all(retained)


def test_an_unchanged_cadence_is_not_republished_to_a_board_that_is_not_waiting(fern):
    """A reading WITHOUT an ack is pre-release firmware or a test's direct ingest: nobody is
    waiting for an answer, so the old economy holds and an unchanged message is not re-sent."""
    for _ in range(3):
        fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.2})
    assert len(cadences(fern)) == 1


def test_an_acked_reading_is_always_answered(fern):
    """The release (#152). A board that acks its cadence is a board that publishes and then
    WAITS for the answer — the reply carries the cadence to sleep on, and the wake ends when it
    lands. So an acked reading must be answered even when nothing changed: the memory of what
    the channel was last told excuses silence only to a board that is not listening for it."""
    for _ in range(3):
        fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.2, "sleep_s": 30})
    assert len(cadences(fern)) == 3


def test_a_changed_cadence_is_republished(fern):
    """Ingested with explicit instants, not delivered back-to-back: two deliveries in the same
    millisecond make a slope of 0.35-per-instant, and the trend bound (#133) then correctly
    refuses to relax for a pot it predicts will be soaked before the next look. A sane
    timeline — recovering gently over ten minutes — is what "the cadence relaxes" is about."""
    from datetime import datetime, timedelta, timezone

    p, s = fern.subscribing(), moisture_sensor(fern)
    now = datetime.now(timezone.utc)
    p.ingest(s, 0.2, now - timedelta(seconds=6_000))  # at the survival floor
    p.ingest(s, 0.55, now)                            # the point of its region, reached calmly
    assert len(cadences(fern)) == 2
    assert cadences(fern)[0] < cadences(fern)[1]


def test_a_sense_request_is_never_retained(fern):
    """A retained 'sense' would re-fire on every wake, forever."""
    fern.subscribing().sense_now()
    assert all(not retain for t, p, retain in fern.sent if p.get("sense"))


# --- judgment and disclosure ----------------------------------------------

def test_it_announces_its_verdict_not_just_a_number(fern):
    """Sensing supplies the number; the band is contributed by the capability that holds a
    stake. The announcement is the agent's, not sensing's — which is why it carries both."""
    fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.10})
    event = fern.sent.to(fern.me.event_topic)[-1]
    assert event["band"] == "LOW" and event["agent"] == "fern"
    assert event["value"] == 0.10


def test_the_reading_is_recorded_as_its_own_assertion(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.123})
    reading = fern.beliefs.current_reading(fern.me.acts_for, MOISTURE)
    assert reading.value == pytest.approx(0.123)
    assert reading.is_fresh(120)


def test_a_malformed_reading_changes_nothing(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"sensor": "x"})  # no value
    assert cadences(fern) == []
    assert fern.beliefs.current_reading(fern.me.acts_for, MOISTURE) is None


# --- one agent, two sensors, two clocks --------------------------------------


def _two_sensor_world(tmp_path, observes="water:SoilMoisture"):
    """A fern watched by a scheduled board AND a push one, which no shipped world does.

    The combination is unexercised rather than untested by oversight — every world here wires one
    sensor per agent — which is exactly why the modules could take each other's sensors unnoticed.

    `observes` picks which of the two cases this is. The default gives both sensors the SAME
    property, which is the one the shapes warn about and where last-writer-wins is the defined
    behaviour; passing a second property gives the ordinary rig — one pot, two things known
    about it — which must be silent and must keep both records.
    """
    import shutil

    from agent import genesis

    src = genesis.world_dir("sensing")
    dst = tmp_path / "two-clocks"
    shutil.copytree(src, dst)
    w = dst / "world.ttl"
    s = w.read_text()

    # TWO sensors means two: the shipped world grew a KY-015's temperature and humidity
    # channels (#51) and they are not what this fixture is about. Left in, `air_temp_fern`
    # would already be observing AirTemperature on this fern, so passing `observes` here would
    # silently produce the two-sensors-one-property case instead of the ordinary rig — the
    # opposite of what the caller asked for.
    #
    # Anchored on the DECLARATION rather than on the bare name. Anchoring on the name meant the
    # first mention won, and #79 gave those sensors an earlier one: `ag:air_sensor_fern` hosts
    # them, so the cut started inside the platform block and took the rest of it with it. The
    # part goes too — a KY-015 hosting two channels this world no longer has would be a
    # platform pointing at nothing.
    for block in ("ag:air_temp_fern a sosa:Sensor , ag:Device ;", "ag:air_humidity_fern a sosa:Sensor , ag:Device ;",
                  "ag:air_sensor_fern a ssn:System ;"):
        start = s.index(block)
        s = s[:start] + s[s.index(" .\n", start) + 3:]
    s = s.replace("    sosa:hosts ag:moisture_sensor_fern , ag:air_sensor_fern ;",
                  "    sosa:hosts ag:moisture_sensor_fern ;")
    s = s.replace(
        "sensing:polls ag:moisture_sensor_fern , ag:air_temp_fern , ag:air_humidity_fern ;",
        "sensing:polls ag:moisture_sensor_fern ;")

    s = s.replace(
        "ag:fern_agent a ag:Agent ;",
        'ag:chatter_fern a sosa:Sensor , ag:Device ;\n'
        '    ag:localId "chatter_fern" ;\n'
        '    mqtt:onBus ag:local_bus ;\n'
        '    sensing:senseMode sensing:PushProcedure ;\n'          # keeps its own clock, takes no orders
        "    sensing:monitors ag:fern ;\n"
        f"    sosa:observes {observes} ;\n"
        '    mqtt:readingTopic "sensors/chatter_fern/reading" .\n\n'
        "ag:fern_agent a ag:Agent ;",
    )
    s = s.replace("sensing:polls ag:moisture_sensor_fern ;",
                  "sensing:polls ag:moisture_sensor_fern , ag:chatter_fern ;")
    w.write_text(s)
    (dst / "hardware.ttl").unlink(missing_ok=True)   # the stand describes one board, not this

    # Gaining a push sensor means gaining sensing:Listening, and that capability asks for a belief the
    # agent did not need before. The refusal to start without it is the self-check working, so
    # the world has to author it — exactly as a sovereign would when adding such a device.
    b = dst / "beliefs" / "fern.ttl"
    b.write_text(b.read_text().replace(
        "sensing:readingGraceS", "sensing:maxReadingAgeS 300 ;\n    sensing:readingGraceS", 1))
    return dst


def _agent_on(world_path, monkeypatch):
    """Built the way an agent builds itself, from a world that is not one of the ratified three."""
    from agent import genesis
    from agent.store import Store

    st = Store()
    genesis.refresh_public(st, world_path)
    genesis.birth(st, world_path, "fern")
    return build_agent("fern", st=st, monkeypatch=monkeypatch)


def test_each_module_takes_only_the_sensors_it_is_for(monkeypatch, tmp_path):
    """The derivation splits the capabilities; the runtime must split the sensors the same way.

    It did not. Both modules took every sensor, and since modules are ordered by
    sorted(capabilities), sensing:Listening claimed the scheduled board too — and listening never
    re-aims, so its cadence was silently never set again.
    """
    agent = _agent_on(_two_sensor_world(tmp_path), monkeypatch)

    by_name = {m.name: m for m in agent.modules}
    assert {"subscribing", "listening"} <= set(by_name), "one of each mode should be derived"

    assert [s.local_id for s in by_name["subscribing"].sensors] == ["moisture_sensor_fern"]
    assert [s.local_id for s in by_name["listening"].sensors] == ["chatter_fern"]


def test_the_scheduled_board_is_still_aimed_when_a_push_sensor_shares_the_agent(
    monkeypatch, tmp_path
):
    """The bug, stated as behaviour: a cadence must still reach the board that takes one."""
    agent = _agent_on(_two_sensor_world(tmp_path), monkeypatch)

    agent.deliver("sensors/moisture_sensor_fern/reading", {"moisture": 0.05})

    commanded = [t for t in agent.sent.topics() if t.endswith("/command")]
    assert commanded == ["sensors/moisture_sensor_fern/command"], (
        "the scheduled board must be re-aimed, and the push one never commanded"
    )


# --- what a person reading the log can tell ----------------------------------------------------


def test_a_reading_is_logged(fern, caplog):
    """The happy path used to log NOTHING.

    Only a cadence CHANGE said anything, and only when it changed — so an agent receiving a
    reading every ten seconds and an agent whose board had been silent for two days produced
    identical logs: none. That is not a cosmetic gap. Diagnosing the second meant reading
    Grafana, which is a poor place to learn that nothing is arriving.
    """
    with caplog.at_level(logging.INFO):
        fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.123})

    line = next((r.getMessage() for r in caplog.records if "0.123" in r.getMessage()), None)
    assert line, "a reading must appear in the log"
    assert "moisture_sensor_fern" in line, "which instrument"
    assert "SoilMoisture" in line, "and which property — 0.123 alone does not say soil or air"
    assert "band=LOW" in line, "and what this agent makes of it"


class _Subscriber:
    """Stands in for the paho client during a re-run of the connect callback."""

    def subscribe(self, topic):
        pass


def test_the_topics_it_subscribed_to_are_logged(fern, caplog):
    """An agent subscribed to the wrong thing looks exactly like a device that never speaks.

    This is the line that tells them apart, and it can be read straight against the ACL and
    against the board's own config without anyone having to guess.
    """
    with caplog.at_level(logging.INFO):
        fern._on_connect(_Subscriber(), None, None, 0, None)

    listening = [r.getMessage() for r in caplog.records if "listening on" in r.getMessage()]
    assert any(sensor_of(fern).reading_topic in m for m in listening)


def test_a_message_nobody_handles_is_not_silent(fern, caplog):
    """The shape a topic disagreement takes: the world names one channel, the device publishes
    on another, both ends look healthy, and the message is dropped without a word."""
    with caplog.at_level(logging.WARNING):
        fern.deliver("sensors/somebody_elses_probe/reading", {"value": 0.5})

    assert any("nothing handled" in r.getMessage() for r in caplog.records)


# --- what the device is told ------------------------------------------------------------------


def commands(agent):
    return agent.sent.to(sensor_of(agent).command_topic)


def test_the_device_is_told_the_verdict_with_the_cadence(fern):
    """One retained message carries both, because it is one instruction to one device.

    A separate topic for the verdict would need its own ACL grant and its own retained slot,
    and would arrive at a different moment from the cadence it belongs with. The board is
    already subscribed here.
    """
    fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.10})
    last = commands(fern)[-1]
    assert last["band"] == "LOW"
    assert last["sleep_s"] > 0


def test_the_verdict_is_retained_like_the_cadence(fern):
    """The whole point on a board that deep-sleeps: it must learn the current verdict when it
    subscribes, not at the next reading it happens to take."""
    fern.deliver(sensor_of(fern).reading_topic, {"moisture": 0.10})
    retained = [r for t, p, r in fern.sent
                if t == sensor_of(fern).command_topic and "band" in p]
    assert retained and all(retained)


def test_a_changed_verdict_is_sent_even_when_the_cadence_did_not_move(fern):
    """The trap in reusing this message, and the reason the dedup had to change.

    Sending was skipped whenever the interval was unchanged, which is right for an interval and
    wrong the moment anything rides along with it. A pot drying from OK to LOW *within one
    cadence band* would have left the old colour on the device indefinitely — the state most
    worth seeing, shown as the state before it.
    """
    p = fern.subscribing()
    p.set_cadence(sensor_of(fern), 60, {"band": "OK"})
    p.set_cadence(sensor_of(fern), 60, {"band": "LOW"})

    assert [c["band"] for c in commands(fern)] == ["OK", "LOW"]


def test_the_same_message_twice_is_sent_once(fern):
    """The other half: nothing changed, so the device is not woken to be told so."""
    p = fern.subscribing()
    for _ in range(3):
        p.set_cadence(sensor_of(fern), 60, {"band": "OK"})
    assert len(commands(fern)) == 1


def test_a_device_whose_agent_holds_no_stake_is_told_only_a_cadence(monkeypatch, tmp_path):
    """The sensing world has no market, so nothing there holds a band.

    The verdict is collected the way every cross-capability opinion is: whoever has one
    contributes. Nobody does here, and the message must not grow an empty field for it.
    """
    agent = _agent_on(_two_sensor_world(tmp_path, observes="water:AirTemperature"), monkeypatch)
    agent.deliver("sensors/moisture_sensor_fern/reading", {"moisture": 0.05})

    sent = [p for t, p, _ in agent.sent if t.endswith("/command")]
    assert sent and all("band" not in p for p in sent)


# --- one subject, two properties: the case an observation's key exists for --------------------


def test_two_properties_of_one_pot_do_not_overwrite_each_other(monkeypatch, tmp_path):
    """A moisture probe and a thermometer on one fern. Both records must survive.

    Keyed by subject alone, the second reading deleted the first and lookups returned whichever
    arrived last. Delivered in this order, asking for moisture would have answered 21.0 — the
    right pot, the wrong quantity, and nothing in the number to say so.
    """
    agent = _agent_on(_two_sensor_world(tmp_path, observes="water:AirTemperature"), monkeypatch)

    agent.deliver("sensors/moisture_sensor_fern/reading", {"moisture": 0.05})
    agent.deliver("sensors/chatter_fern/reading", {"value": 21.0})

    # The pot, not the agent — this world is sensing-only, so nobody acts for anything here.
    pot = sensor_of(agent).subject
    assert agent.beliefs.current_reading(pot, MOISTURE).value == pytest.approx(0.05)
    assert agent.beliefs.current_reading(pot, TEMPERATURE).value == pytest.approx(21.0)


def test_the_announcement_says_which_property_it_is_about(monkeypatch, tmp_path):
    """One event topic now carries two kinds of number, so each has to name itself.

    Nothing downstream could otherwise tell 0.05 from 21.0 except by how implausible it looks,
    and "implausible" is not a unit.
    """
    agent = _agent_on(_two_sensor_world(tmp_path, observes="water:AirTemperature"), monkeypatch)

    agent.deliver("sensors/moisture_sensor_fern/reading", {"moisture": 0.05})
    agent.deliver("sensors/chatter_fern/reading", {"value": 21.0})

    said = {e["property"]: e["value"] for e in agent.sent.to(agent.me.event_topic)}
    assert said == {MOISTURE: 0.05, TEMPERATURE: 21.0}


# --- the trend bound: sleep no longer than the trend allows (#133) ----------

def moisture_sensor(agent):
    """The probe, by what it observes — never sensors[0], which on this board is whichever
    sorted first, and a 0.5 ingested into the THERMOMETER is a frozen greenhouse at maximum
    urgency. The first draft of these tests did exactly that and asserted on the wrong panic."""
    return next(s for s in agent.me.sensors if s.observes == MOISTURE)


def _ingest_pair(fern, first, second, seconds_apart=600):
    """Two readings a stated interval apart, so the slope is a fact and not an accident of
    how fast the test runs. `ingest` exists for exactly this caller — one with no message."""
    from datetime import datetime, timedelta, timezone

    p, s = fern.subscribing(), moisture_sensor(fern)
    now = datetime.now(timezone.utc)
    p.ingest(s, first, now - timedelta(seconds=seconds_apart))
    p.ingest(s, second, now)
    return p


def test_a_fast_drying_pot_is_not_granted_a_long_sleep(fern):
    """The failure #133 names: comfortable now, drying fast, and a sleep granted on the
    current gap alone would end deep in trouble. The trend bound evaluates urgency at the
    PREDICTED end-of-sleep value and grants what that answer earns — so the sawtooth flattens
    BEFORE the band is crossed, not after.

    0.60 to 0.50 in ten minutes: still OK (fern's region floor is 0.45), but at that rate a
    ~500s sleep ends near 0.42 — below the region. The granted sleep must shorten now.
    """
    p = _ingest_pair(fern, 0.60, 0.50)
    with_trend = cadences(fern)[-1]

    calm = _ingest_pair(fern, 0.50, 0.50)  # same state, no movement
    without = cadences(fern)[-1]
    assert with_trend < without, \
        "the same reading earned the same sleep whether or not trouble was approaching"


def test_a_favourable_trend_relaxes_nothing(fern):
    """Tighten-only. A pot recovering toward the aim is predicted to be MORE comfortable at
    wake, and the bound must not turn that prediction into a longer sleep: reading too often
    costs a reading, reading too rarely costs a plant, and a prediction is trusted only in
    the direction where being wrong is cheap."""
    rising = _ingest_pair(fern, 0.46, 0.48)      # below centre, recovering
    with_trend = cadences(fern)[-1]

    still = _ingest_pair(fern, 0.48, 0.48)
    without = cadences(fern)[-1]
    assert with_trend == without


def test_no_slope_means_no_bound(fern):
    """One reading is a position, not a velocity. Before two readings exist — and after every
    restart, since the trend is module memory and the store upserts history away — the cadence
    is exactly the pre-#133 one, honestly reached."""
    p, s = fern.subscribing(), moisture_sensor(fern)
    p.ingest(s, 0.50, None)
    assert cadences(fern)[-1] == cadence_for(fern, 0.50)


def test_the_bound_respects_the_constitutional_floor(fern):
    """A trend however catastrophic tightens to fastSleepS and the constitutional floor,
    never past them — the clamps hold whoever computes the number."""
    p = _ingest_pair(fern, 0.60, 0.30, seconds_apart=60)  # collapsing
    assert cadences(fern)[-1] >= fern.subscribing().min_sleep_s


# --- ignorance is urgent: the opening burst (#137) --------------------------

def test_not_knowing_a_desired_property_is_maximum_urgency(fern):
    """Asked with None, the choir answers the OTHER question — how urgent is not knowing —
    and for a property the agent wants held, the answer is maximal: not knowing whether the
    pot is dying is at least as urgent as knowing it is uncomfortable. A property with no
    region stays silent, exactly as it does for any reading of it."""
    assert fern.urgency(fern.me.acts_for, MOISTURE, None) == 1.0
    assert fern.urgency(fern.me.acts_for, HUMIDITY, None) is None


def test_the_opening_burst_commands_fast_before_any_reading_exists(fern):
    """At birth there is a desired state and an empty sensed graph — the moment of maximum
    uncertainty — and the cadence used to be computed only when a reading arrived, so maximum
    ignorance got no attention policy at all. start() now aims every sensor at once, and
    ignorance earns the fast end: poll often first, to have actual data and a trend to reason
    from."""
    p = fern.subscribing()
    p.start()
    assert cadences(fern)[-1] == p.beliefs.fast_sleep_s


def test_the_burst_relaxes_once_the_property_is_measured(fern):
    """The two forces find their equilibrium — GRADUALLY (#139). Ignorance pressed the cadence
    to the fast end; the first comfortable reading starts the release, bounded per step by the
    family's relaxFactor rather than cliffing straight to the slow end: one reading is a
    point, not a picture, and the trend bound is blind until the second. Fast attack, slow
    release — a few dense readings, geometrically apart, and the slow end is earned."""
    p = fern.subscribing()
    p.start()
    fast = p.beliefs.fast_sleep_s
    assert cadences(fern)[-1] == fast

    fern.deliver(moisture_sensor(fern).reading_topic, {"moisture": 0.55})
    first_release = cadences(fern)[-1]
    assert first_release == int(fast * p.relax_factor), \
        "one comfortable reading must earn one step of release, not the whole cliff"

    granted = first_release
    for _ in range(12):
        fern.deliver(moisture_sensor(fern).reading_topic, {"moisture": 0.55})
        latest = cadences(fern)[-1]
        assert latest <= int(granted * p.relax_factor) or latest == granted
        granted = latest
        if granted == p.beliefs.slow_sleep_s:
            break
    assert granted == p.beliefs.slow_sleep_s, "the release must still REACH the slow end"


def test_tightening_is_never_slewed(fern):
    """The asymmetry is the whole point: a comfortable pot that suddenly reads parched earns
    the fast cadence in ONE step, whatever the release schedule was doing — hesitating in that
    direction costs a plant, and the slew must never be a reason to look away from trouble."""
    p = fern.subscribing()
    fern.deliver(moisture_sensor(fern).reading_topic, {"moisture": 0.55})   # calm-ish
    fern.deliver(moisture_sensor(fern).reading_topic, {"moisture": 0.20})   # survival floor
    assert cadences(fern)[-1] == p.beliefs.fast_sleep_s


def test_an_agent_that_already_knows_opens_calm(monkeypatch):
    """Fresh readings on record at boot — BOTH properties, because fern desires two — earn the
    gap's ordinary answer, not the burst: ignorance is a state, not a ritual, and an agent
    restarting into knowledge it already holds has nothing to be ignorant about.

    Both matter, and the first draft seeded only moisture: the thermometer's ignorance then
    correctly keeps the shared board fast, and before #139 the per-sensor command loop let the
    moisture sensor's calm answer overwrite it — last writer winning over a still-ignorant
    peer. The slew now preserves the tightness, which exposed the test's incomplete premise
    rather than a defect."""
    fern = build_agent("fern", genesis_store(
        {("fern", MOISTURE): 0.55, ("fern", TEMPERATURE): 21.0}), monkeypatch)
    p = fern.subscribing()
    p.start()
    assert cadences(fern)[-1] == p.beliefs.slow_sleep_s


def test_an_agent_with_no_stake_opens_at_its_own_pace(monkeypatch):
    """The recording agent wants nothing, so not knowing is not urgent for it — the burst is
    desire's answer, not a boot ritual for everyone. It still states its policy at start,
    which it never did before: a board is aimed from the first moment rather than running its
    default until a reading happens by."""
    recorder = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    p = recorder.subscribing()
    p.start()
    assert cadences(recorder)[-1] == p.beliefs.slow_sleep_s


# --- the reading says which cadence it was taken under (#135) ---------------

def test_freshness_follows_the_acknowledged_cadence(fern):
    """The board's testimony beats the agent's intent: a reading that says it was taken under
    900s must be held to 900s plus grace, whatever the agent believes it commanded — a command
    the board never received must not make its honest rhythm read as gone-quiet."""
    fern.deliver(moisture_sensor(fern).reading_topic, {"moisture": 0.2, "sleep_s": 900})
    p = fern.subscribing()
    assert p.stale_after_s(fern.me.acts_for, MOISTURE) == 900 + p.beliefs.grace_s


def test_without_an_ack_the_commanded_cadence_still_rules(fern):
    """Old firmware stays legal: absence of the field is the pre-ack world, not an error."""
    fern.deliver(moisture_sensor(fern).reading_topic, {"moisture": 0.2})
    p = fern.subscribing()
    commanded = p.sent_cadence[moisture_sensor(fern).local_id]
    assert p.stale_after_s(fern.me.acts_for, MOISTURE) == commanded + p.beliefs.grace_s


def test_one_mismatched_ack_is_noise_and_two_are_the_detector(fern, caplog):
    """Pre-release firmware acks the OLD value once after every re-aim (its live response
    landed in a fixed window) — expected, silent. The same mismatch twice running is the real
    thing: a cleared retained command (#37) or a firmware clamp, said out loud. The re-send no
    longer needs arranging: every acked reading is answered, because the answer is the release
    (#152)."""
    import logging

    s = moisture_sensor(fern)
    fern.deliver(s.reading_topic, {"moisture": 0.2})            # command 30 goes out
    with caplog.at_level(logging.WARNING):
        fern.deliver(s.reading_topic, {"moisture": 0.2, "sleep_s": 600})   # first mismatch: noise
        assert "twice running" not in caplog.text
        sent_before = len(cadences(fern))
        fern.deliver(s.reading_topic, {"moisture": 0.2, "sleep_s": 600})   # second: the detector
    assert "twice running" in caplog.text
    assert len(cadences(fern)) > sent_before, \
        "the dispute must re-send the command, not keep assuming the board knows it"


def test_an_agreeing_ack_clears_the_dispute(fern):
    """One success resets, exactly as the affordance suspicion does: a board that took the
    command is a board in agreement, whatever the previous wake said."""
    s = moisture_sensor(fern)
    fern.deliver(s.reading_topic, {"moisture": 0.2})
    fern.deliver(s.reading_topic, {"moisture": 0.2, "sleep_s": 600})       # mismatch once
    commanded = fern.subscribing().sent_cadence[s.local_id]
    fern.deliver(s.reading_topic, {"moisture": 0.2, "sleep_s": commanded})  # agreement
    key = s.command_topic or s.local_id
    assert key not in fern.subscribing()._ack_disputed


def test_the_ack_reaches_the_health_series(fern):
    """Beside the commanded cadence, the ack in series form IS the #37 detector on a dashboard:
    the two diverging is a cleared or clamped command, visible instead of silent."""
    s = moisture_sensor(fern)
    fern.deliver(s.reading_topic, {"moisture": 0.2, "sleep_s": 600})
    assert fern.metrics.cadence_acked_s(s.local_id) == 600
    # every sensor sharing the board's channel carries the board's rhythm
    for peer in fern.subscribing()._aimed_with(s):
        assert fern.metrics.cadence_acked_s(peer.local_id) == 600


# --- a cadence that could not be sent is not pretended sent (#103) -----------

def test_nothing_is_recorded_for_a_cadence_that_had_no_channel(fern, caplog):
    """The composition-of-correct-silences, closed at the last link: the driver used to open
    `if command_topic:` and return having published nothing, and the module then recorded the
    cadence as in force and logged it — so the agent believed, reported and freshness-judged a
    rhythm no board was keeping. The shapes refuse the wiring; this is the runtime half."""
    from dataclasses import replace

    p, s = fern.subscribing(), moisture_sensor(fern)
    mute = replace(s, command_topic=None)
    p.sensors = tuple(mute if x.local_id == s.local_id else x for x in p.sensors)
    p.drivers[mute.uri] = p.drivers[s.uri]
    with caplog.at_level(logging.WARNING):
        p.set_cadence(mute, 60, None)
    assert "no channel" in caplog.text
    assert mute.local_id not in p.sent_cadence, \
        "a cadence that never went out must not be recorded as in force"


# --- two probes, two patches, two records (#98) ------------------------------

def test_two_probes_in_two_patches_keep_two_records(monkeypatch):
    """The flicker, ended: the observation is keyed by the PATCH where one is stated, so the
    second probe stops overwriting the first — and the pot answers with the newest witness
    across its patches, which is a choice of witness and deliberately not an aggregation."""
    from datetime import datetime, timedelta, timezone

    from agent.ontology import SENSED_GRAPH, WORLD_GRAPH
    from agent.store import bindings

    st = genesis_store()
    st.update(f"""
        PREFIX ag: <http://example.org/agora#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX sensing: <http://example.org/agora/sensing#>
        PREFIX mqtt: <http://example.org/agora/mqtt#>
        PREFIX scaling: <http://example.org/agora/scaling#>
        PREFIX water: <http://example.org/agora/water#>
        PREFIX unit: <http://qudt.org/vocab/unit/>
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{
            ag:fern_east a sosa:Sample ; sosa:isSampleOf ag:fern .
            ag:fern_west a sosa:Sample ; sosa:isSampleOf ag:fern .
            ag:moisture_sensor_fern sensing:samples ag:fern_east .
            ag:second_probe_fern a sosa:Sensor , ag:Device ; ag:localId "second_probe_fern" ;
                mqtt:onBus ag:local_bus ; sensing:senseMode sensing:ScheduledProcedure ;
                sensing:monitors ag:fern ; sensing:samples ag:fern_west ;
                sosa:observes water:SoilMoisture ;
                scaling:quantityUnit unit:UNITLESS ;
                mqtt:readingTopic "sensors/second_probe_fern/reading" ;
                mqtt:commandTopic "sensors/second_probe_fern/command" .
            ag:fern_agent sensing:polls ag:second_probe_fern .
        }} }} WHERE {{}}""")
    fern = build_agent("fern", st, monkeypatch)
    p = fern.subscribing()
    east = next(s for s in p.sensors if s.local_id == "moisture_sensor_fern")
    west = next(s for s in p.sensors if s.local_id == "second_probe_fern")
    assert east.sample and west.sample and east.sample != west.sample

    now = datetime.now(timezone.utc)
    p.ingest(east, 0.30, now - timedelta(seconds=60))
    p.ingest(west, 0.55, now)

    rows = bindings(fern.store.query(
        "SELECT ?obs WHERE { GRAPH <%s> { ?obs a sosa:Observation ; "
        "sosa:observedProperty <%s> ; sosa:hasSimpleResult ?v } }"
        % (SENSED_GRAPH, MOISTURE)))
    assert len(rows) == 2, "the old keying overwrote one patch's record with the other's"
    # the pot answers with the newest witness among its patches
    assert fern.beliefs.current_reading(fern.me.acts_for, MOISTURE).value == pytest.approx(0.55)


def test_a_device_that_speaks_for_itself_lands_in_phenomenon_time(fern):
    """#101's plumbing, exercised ahead of the first device that uses it: a reading whose
    device supplied its own instant carries sosa:phenomenonTime beside the arrival-stamped
    resultTime — when the result applies to the world, as distinct from when we heard."""
    from datetime import datetime, timedelta, timezone

    from agent.ontology import SENSED_GRAPH
    from agent.store import bindings

    p, s = fern.subscribing(), moisture_sensor(fern)
    arrived = datetime.now(timezone.utc)
    sensed = arrived - timedelta(seconds=42)
    p.observations.record(p.log, s, 0.41, at=arrived, phenomenon_at=sensed)

    rows = bindings(fern.store.query(f"""
SELECT ?rt ?pt WHERE {{ GRAPH <{SENSED_GRAPH}> {{
  ?obs sosa:observedProperty <{MOISTURE}> ;
       sosa:resultTime ?rt .
  OPTIONAL {{ ?obs sosa:phenomenonTime ?pt }} }} }}"""))
    assert rows and rows[0].get("pt"), "the device's own instant was dropped"
    assert rows[0]["pt"] != rows[0]["rt"], "phenomenonTime must be the device's, not arrival"


# --- the board watches the agent's desire (#151) -----------------------------

def test_an_alarmed_channel_is_told_the_region_edges(monkeypatch):
    """The thresholds ride the retained command beside the cadence, and they are DESIRE's
    region edges — the board literally watches what its agent wants held, while both sleep."""
    fern = build_agent("fern", genesis_store({"fern": 0.55}), monkeypatch)
    p, s = fern.subscribing(), moisture_sensor(fern)
    assert s.alarm, "the simulation world promises announce-on-crossing for this device"
    p.set_cadence(s, 600, None)
    sent = [c for c in fern.sent.to(s.command_topic) if "alarm" in c]
    assert sent, "a crossing-watcher must be told its band"
    watch = sent[-1]["alarm"]
    # [low, high, delta]: the band is desire's region, the deviation limit a quarter of its
    # width (sensing:alarmDeltaFraction) — the in-band jolt that is worth waking for.
    assert watch["/moisture"] == [pytest.approx(0.45), pytest.approx(0.65),
                                  pytest.approx(0.05)]
    # and the AIR channel's limits ride the same map — per channel, one retained breath
    assert watch["/temperature"] == [pytest.approx(18.0), pytest.approx(24.0),
                                     pytest.approx(1.5)]


def test_a_repicked_jolt_threshold_rearms_the_watch(monkeypatch):
    """The whole reason the delta is a belief and not a compile-time figure: a review moves it,
    the module re-aims, and the corrected threshold reaches the board in the next retained
    command — being wrong about the estimate costs a message, never a reflash."""
    from agent.ontology import beliefs_graph
    from packages.capability.sensing.terms import term as sensing_term

    fern = build_agent("fern", genesis_store({"fern": 0.55}), monkeypatch)
    p, s = fern.subscribing(), moisture_sensor(fern)
    p.observations.record(p.log, s, 0.55)   # the re-aim needs a reading to re-aim from
    p.set_cadence(s, 600, None)
    assert fern.sent.to(s.command_topic)[-1]["alarm"]["/moisture"][2] == pytest.approx(0.05)

    delta = sensing_term("alarmDeltaFraction")
    fern.store.update(f"""
DELETE {{ GRAPH <{beliefs_graph(fern.id)}> {{ ?a <{delta}> ?old }} }}
INSERT {{ GRAPH <{beliefs_graph(fern.id)}> {{ ?a <{delta}> 0.5 }} }}
WHERE  {{ GRAPH <{beliefs_graph(fern.id)}> {{ ?a <{delta}> ?old }} }}""")
    p.on_belief_revised(delta, 0.5)

    # half the 0.45..0.65 band's width now, on the same channel, without a reflash
    assert fern.sent.to(s.command_topic)[-1]["alarm"]["/moisture"][2] == pytest.approx(0.1)


def test_an_agent_with_no_pick_commands_band_only_alarms(monkeypatch):
    """Absence is a statement, not an error: no jolt threshold means the board watches the
    band's edges and nothing else — and no figure is invented from the family's default,
    because a pick must be the agent's own to be revisable."""
    from packages.capability.sensing.beliefs import ALARM_BLOCK
    from packages.capability.sensing.module import SubscribingModule
    from packages.capability.sensing.terms import term as sensing_term
    from agent.ontology import beliefs_graph

    fern = build_agent("fern", genesis_store({"fern": 0.55}), monkeypatch)
    fern.store.update(f"""
DELETE WHERE {{ GRAPH <{beliefs_graph(fern.id)}> {{
  ?a <{sensing_term("alarmDeltaFraction")}> ?old }} }}""")
    assert fern.beliefs.read_optional(ALARM_BLOCK) is None
    p = SubscribingModule(fern)
    s = moisture_sensor(fern)
    p.set_cadence(s, 600, None)
    watch = fern.sent.to(s.command_topic)[-1]["alarm"]
    assert watch["/moisture"] == [pytest.approx(0.45), pytest.approx(0.65)]


def test_an_agent_with_no_stake_commands_no_alarm(monkeypatch, tmp_path):
    """The recording agent wants nothing, so there are no edges to watch — the choir answers
    None and the command carries no thresholds, whatever the device promises."""
    agent = _agent_on(_two_sensor_world(tmp_path, observes="water:AirTemperature"), monkeypatch)
    p = agent.subscribing()
    s = p.sensors[0]
    p.set_cadence(s, 600, None)
    assert all("watch" not in c for c in agent.sent.to(s.command_topic))


def test_an_alarm_armed_watch_is_live_whatever_the_heartbeat(monkeypatch):
    """#151 reaching #132: a dose landing crosses the band and the board announces within its
    watch period, so a held claim need not wait for a fast-acked cadence — the promise IS the
    live watch, once the band has actually been sent."""
    fern = build_agent("fern", genesis_store({"fern": 0.55}), monkeypatch)
    p, s = fern.subscribing(), moisture_sensor(fern)
    assert not p.watch_is_live(fern.me.acts_for, MOISTURE), \
        "before anything is sent there is no promise to lean on"
    p.set_cadence(s, 600, None)   # the band goes out with the cadence
    assert p.watch_is_live(fern.me.acts_for, MOISTURE)

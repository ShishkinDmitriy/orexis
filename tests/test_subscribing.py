"""perception:Subscribing — attention as the agent's own decision, bounded by the constitution.

The agent states an interval and the device keeps to it. What is the agent's here is the
*policy* — how often to look, and how that moves with trouble; what it delegates is only the
timekeeping. Driven through a real agent, so the numbers come from the agent's own beliefs and
the bounds from the ontology — neither is written down here.
"""

import logging
from dataclasses import replace

import pytest

from conftest import MOISTURE, TEMPERATURE, build_agent, genesis_store


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_store(), monkeypatch)


def sensor_of(agent):
    return agent.me.sensors[0]


def cadence_for(agent, value, observed_property=MOISTURE):
    """The cadence the agent would choose for a reading of its own subject.

    Three arguments now, and deliberately: perception asks about a *property of* a subject,
    because whether a number is trouble is the stakeholder's answer, and a stake is held in
    one property. A thermometer's reading of the same pot is not the bidder's business.
    """
    return agent.subscribing().cadence_for(agent.me.acts_for, observed_property, value)


def cadences(agent):
    """Every cadence the agent has commanded, in order."""
    return [p["sleep_s"] for p in agent.sent.to(sensor_of(agent).command_topic)
            if "sleep_s" in p]


# --- the policy ------------------------------------------------------------

def test_it_watches_closely_when_thirsty(fern):
    assert cadence_for(fern, 0.35) == 30  # at its own low band -> its fastest
    assert cadence_for(fern, 0.65) == 600  # at its high band -> its slowest


def test_attention_scales_with_trouble(fern):
    assert cadence_for(fern, 0.40) < cadence_for(fern, 0.60)


def test_attention_without_a_stake_falls_back_to_the_slow_cadence(fern):
    """Urgency is supplied by whoever holds a band. Asked about a subject it has no stake in,
    the agent has no opinion — and an agent with no opinion does not watch closely."""
    p = fern.subscribing()
    assert p.cadence_for("http://example.org/agora#someone_elses_plant", MOISTURE, 0.0) == \
        p.beliefs.slow_sleep_s


def test_a_property_it_has_no_stake_in_gets_no_verdict(fern):
    """Its own pot, its own sensor — but a temperature, and its band is a band of moisture.

    The distinction that matters is *no opinion* versus *an opinion of zero*, which is why this
    tests for None rather than for a cadence. 21.0 read as a moisture fraction lands far above
    target and so scores as perfectly comfortable: the wrong answer and the right number, which
    is the worst way for a bug to present. An assertion about the resulting cadence passes
    whether or not the property is checked, and one about urgency does not.
    """
    assert fern.urgency(fern.me.acts_for, TEMPERATURE, 21.0) is None
    assert fern.annotations(fern.me.acts_for, TEMPERATURE, 21.0) == {}

    assert fern.urgency(fern.me.acts_for, MOISTURE, 0.10) is not None
    assert fern.annotations(fern.me.acts_for, MOISTURE, 0.10) == {"band": "LOW"}


def test_the_bounds_come_from_the_ontology_not_the_code(fern):
    """MIN/MAX are stated in capabilities/perception/ontology.ttl and read at startup."""
    p = fern.subscribing()
    assert (p.min_sleep_s, p.max_sleep_s) == (10, 900)


def test_no_agent_can_exceed_the_constitutional_ceiling(fern):
    """Even an agent that wants to nap forever is clamped — the shapes reject such beliefs
    too, so this is the second of three independent guards (the third is the firmware)."""
    p = fern.subscribing()
    p.beliefs = replace(p.beliefs, slow_sleep_s=99_999)
    assert cadence_for(fern, 0.99) == p.max_sleep_s


def test_no_agent_can_hammer_its_sensor_flat(fern):
    p = fern.subscribing()
    p.beliefs = replace(p.beliefs, fast_sleep_s=1)
    assert cadence_for(fern, 0.0) == p.min_sleep_s


# --- the two levers --------------------------------------------------------

def test_cadence_is_retained_so_a_sleeping_board_gets_it(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.2})
    retained = [r for t, p, r in fern.sent
                if t == sensor_of(fern).command_topic and "sleep_s" in p]
    assert retained and all(retained)


def test_an_unchanged_cadence_is_not_republished(fern):
    for _ in range(3):
        fern.deliver(sensor_of(fern).reading_topic, {"value": 0.2})
    assert len(cadences(fern)) == 1


def test_a_changed_cadence_is_republished(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.2})   # thirsty
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.9})   # comfortable
    assert len(cadences(fern)) == 2
    assert cadences(fern)[0] < cadences(fern)[1]


def test_a_sense_request_is_never_retained(fern):
    """A retained 'sense' would re-fire on every wake, forever."""
    fern.subscribing().sense_now()
    assert all(not retain for t, p, retain in fern.sent if p.get("sense"))


# --- judgment and disclosure ----------------------------------------------

def test_it_announces_its_verdict_not_just_a_number(fern):
    """Perception supplies the number; the band is contributed by the capability that holds a
    stake. The announcement is the agent's, not perception's — which is why it carries both."""
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.10})
    event = fern.sent.to(fern.me.event_topic)[-1]
    assert event["band"] == "LOW" and event["agent"] == "fern"
    assert event["value"] == 0.10


def test_the_reading_is_recorded_as_its_own_assertion(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.123})
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
    for block in ("ag:air_temp_fern a perception:Sensor ;", "ag:air_humidity_fern a perception:Sensor ;",
                  "ag:air_sensor_fern a sosa:Platform ;"):
        start = s.index(block)
        s = s[:start] + s[s.index(" .\n", start) + 3:]
    s = s.replace("    sosa:hosts ag:moisture_sensor_fern , ag:air_sensor_fern ;",
                  "    sosa:hosts ag:moisture_sensor_fern ;")
    s = s.replace(
        "perception:polls ag:moisture_sensor_fern , ag:air_temp_fern , ag:air_humidity_fern ;",
        "perception:polls ag:moisture_sensor_fern ;")

    s = s.replace(
        "ag:fern_agent a ag:Agent ;",
        'ag:chatter_fern a perception:Sensor ;\n'
        '    ag:localId "chatter_fern" ;\n'
        '    mqtt:onBus ag:local_bus ;\n'
        '    perception:senseMode perception:Push ;\n'          # keeps its own clock, takes no orders
        "    perception:monitors ag:fern ;\n"
        f"    sosa:observes {observes} ;\n"
        '    mqtt:readingTopic "sensors/chatter_fern/reading" .\n\n'
        "ag:fern_agent a ag:Agent ;",
    )
    s = s.replace("perception:polls ag:moisture_sensor_fern ;",
                  "perception:polls ag:moisture_sensor_fern , ag:chatter_fern ;")
    w.write_text(s)
    (dst / "hardware.ttl").unlink(missing_ok=True)   # the stand describes one board, not this

    # Gaining a push sensor means gaining perception:Listening, and that capability asks for a belief the
    # agent did not need before. The refusal to start without it is the self-check working, so
    # the world has to author it — exactly as a sovereign would when adding such a device.
    b = dst / "beliefs" / "fern.ttl"
    b.write_text(b.read_text().replace(
        "perception:readingGraceS", "perception:maxReadingAgeS 300 ;\n    perception:readingGraceS", 1))
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
    sorted(capabilities), perception:Listening claimed the scheduled board too — and listening never
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

    agent.deliver("sensors/moisture_sensor_fern/reading", {"value": 0.05})

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
        fern.deliver(sensor_of(fern).reading_topic, {"value": 0.123})

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
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.10})
    last = commands(fern)[-1]
    assert last["band"] == "LOW"
    assert last["sleep_s"] > 0


def test_the_verdict_is_retained_like_the_cadence(fern):
    """The whole point on a board that deep-sleeps: it must learn the current verdict when it
    subscribes, not at the next reading it happens to take."""
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.10})
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
    agent.deliver("sensors/moisture_sensor_fern/reading", {"value": 0.05})

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

    agent.deliver("sensors/moisture_sensor_fern/reading", {"value": 0.05})
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

    agent.deliver("sensors/moisture_sensor_fern/reading", {"value": 0.05})
    agent.deliver("sensors/chatter_fern/reading", {"value": 21.0})

    said = {e["property"]: e["value"] for e in agent.sent.to(agent.me.event_topic)}
    assert said == {MOISTURE: 0.05, TEMPERATURE: 21.0}

"""One device reports two properties, and each sensor takes its own value out of one message.

The board is one MQTT client with one credential, so it publishes once however many peripherals
it carries. What separates the values is `mqtt:readingPointer` — a JSON Pointer (RFC 6901), which
identifies exactly ONE value, which is exactly what a device reports per property.

These cover the two halves that were broken: resolving the pointer, and offering one message to
every sensor that owns the channel rather than only the first. See
knowledge/decisions/a-reading-is-one-value-so-it-is-pointed-at.md and issue #51.
"""

import json

import pytest

from agent.ontology import SENSED_GRAPH
from packages.capability.sensing.pointer import DEFAULT_POINTER, PointerError, resolve
from agent.store import bindings
from packages.capability.sensing.wiring import Sensor

from conftest import build_agent, genesis_store, query_fn, wired_sensors, load_wired, reading_of

AIR_TEMP = "http://example.org/orexis/water#AirTemperature"
AIR_HUMIDITY = "http://example.org/orexis/water#AirHumidity"
# The mode every shipped board states: it keeps an interval its agent gives it.
SCHEDULED = "http://example.org/orexis/sensing#ScheduledProcedure"
MOISTURE = "http://example.org/orexis/water#SoilMoisture"


# --- the pointer itself ----------------------------------------------------

def test_a_pointer_selects_a_named_field():
    assert resolve("/temperature", {"temperature": 21.4, "humidity": 0.46}) == 21.4


def test_a_pointer_walks_into_nesting():
    """A flat field name could not express this, which is most of why it is a pointer."""
    assert resolve("/readings/rh", {"readings": {"rh": 0.46}}) == 0.46


def test_a_pointer_indexes_an_array():
    assert resolve("/samples/1", {"samples": [1.0, 2.5, 3.0]}) == 2.5


def test_the_escapes_are_decoded_in_the_order_the_rfc_states():
    """`~1` becomes `/` FIRST, then `~0` becomes `~` — and the order is the whole trap.

    Decoded the other way round, the `~01` below would become `~1` and then `/`, selecting a
    field that was never asked for. RFC 6901 fixes the order precisely so a document may hold
    a key with a literal tilde-one in it.
    """
    assert resolve("/a~1b", {"a/b": 1.0}) == 1.0        # ~1 is a slash
    assert resolve("/a~0b", {"a~b": 2.0}) == 2.0        # ~0 is a tilde
    assert resolve("/a~01b", {"a~1b": 3.0}) == 3.0      # NOT {"a/b"}, which reversing would give


def test_the_default_is_what_every_single_property_board_already_sends():
    assert DEFAULT_POINTER == "/value"
    assert resolve(DEFAULT_POINTER, {"value": 0.183, "sensor": "probe"}) == 0.183


@pytest.mark.parametrize("pointer, doc", [
    ("/humidity", {"temperature": 21.4}),          # the field is simply absent
    ("/a/b", {"a": {"c": 1}}),                     # absent one level down
    ("/samples/9", {"samples": [1.0]}),            # past the end
    ("/samples/rh", {"samples": [1.0]}),           # not an index
    ("/a/b", {"a": 3.0}),                          # nothing left to select from
    ("temperature", {"temperature": 21.4}),        # not a pointer at all — no leading slash
    ("", {"value": 1.0}),                          # the RFC's whole-document pointer
])
def test_a_pointer_that_does_not_identify_a_value_is_refused(pointer, doc):
    """Refused, never defaulted. A pointer that misses is a world stating something the device
    does not send, and answering 0.0 would record that as a measurement."""
    with pytest.raises((PointerError, ValueError)):
        float(resolve(pointer, doc))


# --- one message, several sensors ------------------------------------------

def _fern():
    return load_wired(query_fn(genesis_store(world="sensing")), "fern")


def test_the_shipped_world_reads_three_properties_off_one_board():
    me = _fern()
    assert {s.observes for s in me.sensors} == {MOISTURE, AIR_TEMP, AIR_HUMIDITY}
    # one channel, three sensors — the board publishes once
    assert len({s.reading_topic for s in me.sensors}) == 1


def test_the_probe_names_its_field_and_the_default_survives_for_the_unnamed():
    """The probe states /moisture now — named for what it measures, like /temperature beside
    it — and the anonymous /value default remains exactly what it always was: the reading of a
    device that states nothing, unchanged by this term existing."""
    probe = next(s for s in _fern().sensors if s.observes == MOISTURE)
    assert probe.reading_pointer == "/moisture"


def test_one_message_produces_an_observation_for_every_sensor_on_the_channel(monkeypatch):
    """The bug, stated as behaviour: `handle` returned after the first owning sensor.

    Two sensors sharing a topic meant the second never saw a message and recorded nothing —
    silently, because the topic HAD been handled, so nothing upstream complained.
    """
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    fern = next(s.subject for s in wired_sensors(agent))

    agent.deliver("sensors/moisture_sensor_fern/reading",
                  {"moisture": 0.183, "temperature": 21.4, "humidity": 0.46,
                   "sensor": "moisture_sensor_fern"})

    # all three survive AT ONCE — the point of keying an observation by subject AND property
    assert reading_of(agent, subject_uri=fern, observed_property=MOISTURE).value == pytest.approx(0.183)
    assert reading_of(agent, subject_uri=fern, observed_property=AIR_TEMP).value == pytest.approx(21.4)
    assert reading_of(agent, subject_uri=fern, observed_property=AIR_HUMIDITY).value == pytest.approx(0.46)


def test_values_from_one_read_carry_one_instant(monkeypatch):
    """A DHT11 cannot be asked for temperature alone, so its two values are one measurement.

    The part returns a single 40-bit frame — humidity in `data[0..1]`, temperature in
    `data[2..3]`, checksum in `data[4]` — filled by one transaction. The firmware's two calls
    are one conversation: the Adafruit driver serves the second from the buffer the first
    filled, and refuses to go back to the wire inside `MIN_INTERVAL`, which is the same two
    seconds `dht11:Dht11` states as its `ssn-system:Frequency`.

    So the values are simultaneous BY CONSTRUCTION, and stamping them separately records a
    difference that did not happen. It is not a rounding matter: `handle` loops the sensors and
    each write called `datetime.now()` for itself, so the gap was however long the loop took —
    #88's end-to-end run put two points 25ms apart in the series store, from one physical read.

    The message is the measurement. One arrival, one instant, however many values it carried.
    """
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    fern = next(s.subject for s in wired_sensors(agent))

    agent.deliver("sensors/moisture_sensor_fern/reading",
                  {"moisture": 0.183, "temperature": 21.4, "humidity": 0.46,
                   "sensor": "moisture_sensor_fern"})

    stamps = {reading_of(agent, subject_uri=fern, observed_property=p).result_time
              for p in (MOISTURE, AIR_TEMP, AIR_HUMIDITY)}
    assert len(stamps) == 1, f"one read, {len(stamps)} instants: {sorted(map(str, stamps))}"


def test_a_sensor_whose_field_is_missing_records_nothing_and_says_so(monkeypatch, caplog):
    """One sensor missing its field while its neighbours read fine is the failure a shared
    payload makes possible, so the warning has to name WHICH sensor found nothing."""
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    fern = next(s.subject for s in wired_sensors(agent))

    with caplog.at_level("WARNING"):
        agent.deliver("sensors/moisture_sensor_fern/reading", {"moisture": 0.183})

    assert reading_of(agent, subject_uri=fern, observed_property=MOISTURE).value == pytest.approx(0.183)
    assert reading_of(agent, subject_uri=fern, observed_property=AIR_TEMP) is None
    assert "air_temp_fern" in caplog.text and "/temperature" in caplog.text


def test_the_channel_is_claimed_even_when_no_sensor_could_read_it(monkeypatch, caplog):
    """`handle` returns *this channel was mine*, which is about addressing and not success —
    otherwise the runtime would report an unreadable payload as an unrouted topic."""
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    with caplog.at_level("WARNING"):
        agent.deliver("sensors/moisture_sensor_fern/reading", {"nothing": "useful"})
    assert "nothing handled a message" not in caplog.text


# --- a cadence belongs to the board ----------------------------------------

def test_one_board_is_aimed_once_however_many_sensors_it_carries(monkeypatch):
    """Three sensors, one command topic, one retained instruction.

    Aimed per sensor, each would compute its own interval from its own urgency and publish it
    retained to the same topic — last writer winning, on every message.
    """
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    agent.sent.clear()

    agent.deliver("sensors/moisture_sensor_fern/reading",
                  {"moisture": 0.183, "temperature": 21.4, "humidity": 0.46})

    cadences = [m for m in agent.sent if m[0] == "sensors/moisture_sensor_fern/command"]
    assert len(cadences) == 1, f"the board was instructed {len(cadences)} times"


def test_the_tightest_cadence_on_a_board_wins(monkeypatch):
    """If anything on this board is urgent, the board watches closely.

    The properties that are not urgent are then read more often than they need to be, which
    costs a reading — the only safe direction to be wrong in.
    """
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    subscribing = agent.subscribing()
    sensors = {s.observes: s for s in subscribing.sensors}

    slow = subscribing.cadence_for(sensors[AIR_TEMP].subject, AIR_TEMP, 21.4)
    agent.sent.clear()
    agent.deliver("sensors/moisture_sensor_fern/reading",
                  {"moisture": 0.183, "temperature": 21.4, "humidity": 0.46})

    sent = [m for m in agent.sent if m[0] == "sensors/moisture_sensor_fern/command"]
    assert sent, "the board must be aimed"
    assert sent[0][1]["sleep_s"] <= slow
    assert sent[0][2] is True, "a cadence is retained, or a sleeping board never hears it"


def test_the_series_store_is_told_which_property_each_reading_is(monkeypatch):
    """Two fractions in the same 0-1 range, and nothing in either number says which it is.

    The reading went to Influx tagged by plant and sensor only, into a measurement called
    `soil_moisture` — so an air temperature of 21.4 was written as this fern's soil moisture,
    and every dashboard and later query would read it as one. The belief base was always fine;
    it keys by subject AND property. The series store, which is the record, was not.
    """
    from packages.capability.sensing import observation

    written = []

    class Recorder:
        def __init__(self, *a, **k):
            pass

        def write_reading(self, plant_id, sensor, value, observed_property, at=None):
            written.append((sensor, value, observed_property, at))

        def write_agent_health(self, *a, **k):
            pass

        def close(self):
            pass

    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    monkeypatch.setattr(observation, "InfluxWriter", Recorder)
    agent.subscribing().observations = observation.Observations(agent)

    agent.deliver("sensors/moisture_sensor_fern/reading",
                  {"moisture": 0.183, "temperature": 21.4, "humidity": 0.46})

    by_property = {p: v for _, v, p, _ in written}
    assert by_property == {"SoilMoisture": pytest.approx(0.183),
                           "AirTemperature": pytest.approx(21.4),
                           "AirHumidity": pytest.approx(0.46)}

    # And the instant travels with them. Left to the store, a point is stamped on RECEIPT, so
    # one message became three times here and a fourth in the belief base. The series is the
    # record a person actually looks at, so it is the one that must not invent a difference.
    stamps = {at for _, _, _, at in written}
    assert len(stamps) == 1 and None not in stamps, f"one read, series stamps: {stamps}"


def test_a_sensor_with_no_command_channel_is_aimed_alone(monkeypatch):
    """The grouping is by command topic, so a sensor without one is a group of one — and the
    driver sends nothing for it. Guards against grouping every unaimable sensor together."""
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    subscribing = agent.subscribing()
    loose = Sensor(uri="urn:loose", local_id="loose", subject="urn:fern", subject_id="fern",
                   observes=AIR_TEMP)
    assert subscribing._aimed_with(loose) == (loose,)


def test_an_observation_says_which_procedure_made_it(monkeypatch):
    """A reading records HOW it was taken, not only what and when.

    `sosa:usedProcedure` carries the sensor's sense mode, and the distinction it preserves is
    not recoverable from the number: under `ScheduledProcedure` a reading that fails to arrive
    means the board is late, under `PushProcedure` it may mean nothing happened worth
    reporting. Before this the answer existed only by joining back to the sensor, which is one
    join away from nobody making it.

    Driven through the real message path rather than the writer, because the value comes off
    `Sensor.sense_mode` — calling the writer directly would prove only that its own argument
    arrives where it was put.
    """
    agent = build_agent("fern", genesis_store(world="sensing"), monkeypatch)
    agent.deliver("sensors/moisture_sensor_fern/reading",
                  {"moisture": 0.183, "temperature": 21.4, "humidity": 0.46})

    # `:sensed` is the agent's own graph and not one of the public five, so it is NAMED here.
    # The rule against wrapping a SELECT in a GRAPH clause is about the public graphs, where
    # narrowing silently drops facts that live in a sibling; this one has to be asked for.
    rows = bindings(agent.beliefs.query(f"""
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        SELECT ?proc WHERE {{ GRAPH <{SENSED_GRAPH}> {{
          ?obs a sosa:Observation ; sosa:usedProcedure ?proc }} }}"""))
    assert rows, "no observation cited a procedure"
    cited = {r["proc"] for r in rows}

    # Every sensor on this board keeps the interval it is given, so all three cite one mode —
    # and the assertion is against what the SENSORS say rather than a constant, so a world that
    # rewires its board moves both sides together.
    assert cited == {s.sense_mode for s in wired_sensors(agent)}
    assert cited == {SCHEDULED}, "the shipped board keeps an interval it is given"

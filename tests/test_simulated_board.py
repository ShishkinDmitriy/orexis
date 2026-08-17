"""A stand-in board reports several properties down one line, and each lands where it is aimed.

The claim `firmware/simulated-sensor/simulator.py` makes about itself is that nothing downstream
can tell it from hardware. That claim went quietly false when the real firmware learned to send
three values and this still sent one — nothing noticed, because no world had asked it for more.
These are about the half a world cannot check: what the board actually puts on the wire.

Imported by path, like the valve's tests: firmware is not a package and must never become one.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

SIMULATOR_PY = (Path(__file__).resolve().parents[1]
                / "firmware" / "simulated-sensor" / "simulator.py")


def _load():
    spec = importlib.util.spec_from_file_location("_sim_sensor", SIMULATOR_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sim = _load()


# --- placing a value where a pointer says ----------------------------------
#
# The mirror of `agent/pointer.py`, and deliberately a second implementation: a board does not
# import the reader's code, and one that could would stop standing in for something that cannot.

def test_a_pointer_places_a_named_field():
    doc: dict = {}
    sim.place(doc, "/temperature", 21.4)
    assert doc == {"temperature": 21.4}


def test_a_pointer_makes_the_objects_on_the_way():
    doc: dict = {}
    sim.place(doc, "/air/temperature", 21.4)
    assert doc == {"air": {"temperature": 21.4}}


def test_the_escapes_are_decoded_in_the_order_the_rfc_states():
    """`~1` becomes `/` FIRST, then `~0` becomes `~`. Reversed, a literal `~1` written `~01`
    decodes to a separator and the value lands in a nested object nobody reads."""
    doc: dict = {}
    sim.place(doc, "/a~01b", 1.0)
    assert doc == {"a~1b": 1.0}


@pytest.mark.parametrize("pointer", ["value", "", "temperature"])
def test_a_pointer_that_does_not_start_with_a_slash_is_refused(pointer):
    with pytest.raises(ValueError):
        sim.place({}, pointer, 1.0)


def test_a_pointer_through_a_value_is_refused():
    """`/value/deeper` where `/value` is already a number. Silently replacing it would drop the
    reading a sensor is actually waiting for."""
    doc = {"value": 0.4}
    with pytest.raises(ValueError):
        sim.place(doc, "/value/deeper", 1.0)


# --- what the board reports -------------------------------------------------

def _device(values, **env):
    """A simulator configured as compose configures one, without a broker.

    `run()` is never called, so nothing connects; this is about what `_publish` composes and how
    `_control` and `_receive` move the values it holds.
    """
    environ = {"SIM_SENSOR_ID": "board_x",
               "SIM_READING_TOPIC": "sensors/board_x/reading",
               "SIM_VALUES": json.dumps(values),
               "MQTT_USERNAME": "u", "MQTT_PASSWORD": "p",
               # A perfect instrument unless a test says otherwise: the grain and the spikes
               # are real defaults, and exact-value assertions must not chase them.
               "SIM_NOISE_SPAN": "0", "SIM_SPIKE_CHANCE": "0",
               **env}
    published: list[tuple[str, str]] = []
    with pytest.MonkeyPatch.context() as mp:
        for k, v in environ.items():
            mp.setenv(k, v)
        device = sim.SimulatedSensor()
    device.client.publish = lambda topic, payload, qos=0: published.append((topic, payload))
    return device, published


MOISTURE = {"pointer": "/value", "min": 0.0, "max": 1.0, "initial": 0.45,
            "loses": 0.12, "litres": 2.0}
# Deliberately swing-less: a swing makes a reading depend on the wall clock, and the shared
# fixture must publish the same bytes at noon and at midnight. The diurnal cycle has its own
# test, on its own Value.
TEMPERATURE = {"pointer": "/temperature", "min": -10.0, "max": 45.0, "initial": 21.0}


def test_one_message_carries_every_property_the_board_reports():
    """One message and not one per value, because that is what a board does: it wakes once,
    reads what it is wired to, and spends one transmission on the lot."""
    device, published = _device([MOISTURE, TEMPERATURE])
    device._publish()

    assert len(published) == 1, "a board sends one message, however many things it read"
    topic, payload = published[0]
    assert topic == "sensors/board_x/reading"
    assert json.loads(payload) == {"sensor": "board_x", "sleep_s": 60,
                                   "value": 0.45, "temperature": 21.0}


def test_a_single_property_board_sends_exactly_what_it_always_did():
    """The shape a probe has always published — plus, since #135, the cadence it was taken
    under. A list of one is not a special case."""
    device, published = _device([MOISTURE])
    device._publish()
    assert json.loads(published[0][1]) == {"sensor": "board_x", "sleep_s": 60, "value": 0.45}


def test_the_physics_run_on_the_clock_not_on_the_readings():
    """A pot loses what the day costs it however often anyone looks. The old per-call drift
    made a closely-watched pot dry faster than an ignored one — backwards, and unmissable once
    the agents started varying how closely they watch."""
    device, _ = _device([MOISTURE], SIM_TIMESCALE="24")
    pot = device.values[0]
    pot.advance(3600.0)  # one real hour = one simulated day at timescale 24
    assert pot.value == pytest.approx(0.45 - 0.12)
    # and a hundred small steps cost exactly what one big one does
    other = sim.Value(dict(MOISTURE), timescale=24.0)
    for _ in range(100):
        other.advance(36.0)
    assert other.value == pytest.approx(pot.value)


def test_a_temperature_has_afternoons_not_a_trend():
    """The swing is a position in the day, not an accumulation: read at two ends of the cycle
    it differs, integrated over any whole day it cancels."""
    room = sim.Value(dict(TEMPERATURE, swing=4.0), timescale=24.0)
    morning = room.read(0.0)             # sim midnight: base
    afternoon = room.read(86400 * 0.25)  # a quarter-day in: the peak of the sine
    assert morning == pytest.approx(21.0)
    assert afternoon == pytest.approx(25.0)
    room.advance(86400.0)  # a whole simulated day of physics moves a swung value not at all
    assert room.value == pytest.approx(21.0)


def test_the_instrument_grain_touches_the_report_and_never_the_world():
    """Measurement error is about the reading: the spike is on the wire, and the value the
    physics hold is untouched — error that fed back would be drift wearing a disguise."""
    device, published = _device([MOISTURE], SIM_SPIKE_CHANCE="1", SIM_SPIKE_SPAN="0.25")
    device.rng = __import__("random").Random(7)
    device._publish()
    reported = json.loads(published[0][1])["value"]
    assert abs(reported - 0.45) > 0.2, "a certain spike must actually spike"
    assert device.values[0].value == pytest.approx(0.45), "the world must hold its value"


def test_rain_arrives_exactly_as_a_dose_does():
    """The meddler's channel: the soil cannot tell a bought litre from a kind stranger's, and
    the sensor takes both through the same receive path — 300 ml against 2 L/fraction."""
    from types import SimpleNamespace

    device, _ = _device([MOISTURE], SIM_RAIN_TOPIC="rain/board_x")
    device._on_message(None, None, SimpleNamespace(topic="rain/board_x",
                                                   payload=json.dumps({"ml": 300}).encode()))
    assert device.values[0].value == pytest.approx(0.45 + 0.3 / 2.0)


def test_a_value_is_clamped_by_its_own_range_not_by_a_fraction():
    device, _ = _device([TEMPERATURE])
    device.values[0].value = 99.0
    assert device.values[0].clamp(99.0) == 45.0
    assert device.values[0].clamp(-99.0) == -10.0


# --- water reaches soil, and nothing else -----------------------------------

def test_a_dose_moves_only_what_a_litre_is_worth_something_to():
    """A thermometer sharing the board is not cooled by watering the plant. A simulation in
    which it was would be teaching an agent something false about the world."""
    device, _ = _device([MOISTURE, TEMPERATURE])
    before = {v.pointer: v.value for v in device.values}

    device._receive(1000.0)  # a litre

    after = {v.pointer: v.value for v in device.values}
    assert after["/value"] == pytest.approx(before["/value"] + 1.0 / 2.0)
    assert after["/temperature"] == before["/temperature"], "watering a pot warmed the air"


# --- steering the scenario ---------------------------------------------------

def test_a_control_verb_aims_at_the_default_value_when_it_says_nothing():
    """Every scenario that steers a single-property device keeps working unchanged."""
    device, _ = _device([MOISTURE, TEMPERATURE])
    device._control({"value": 0.9})
    assert {v.pointer: v.value for v in device.values}["/value"] == 0.9


def test_a_control_verb_reaches_another_property_with_at():
    device, _ = _device([MOISTURE, TEMPERATURE])
    device._control({"value": 30.0, "at": "/temperature"})
    held = {v.pointer: v.value for v in device.values}
    assert held["/temperature"] == 30.0
    assert held["/value"] == 0.45, "aiming at one property moved another"


def test_a_reset_puts_the_whole_board_back():
    """Not only what `at` names: a board half-reset is a scenario nobody meant to set up."""
    device, _ = _device([MOISTURE, TEMPERATURE])
    device._control({"value": 0.9})
    device._control({"value": 30.0, "at": "/temperature"})
    device._control({"reset": True})
    assert {v.pointer: v.value for v in device.values} == {"/value": 0.45, "/temperature": 21.0}


def test_aiming_at_a_property_the_board_does_not_report_changes_nothing(caplog):
    device, _ = _device([MOISTURE])
    device._control({"value": 5.0, "at": "/humidity"})
    assert device.values[0].value == 0.45
    assert "nothing is reported at /humidity" in caplog.text


# --- what a board cannot be ---------------------------------------------------

def test_a_board_that_reports_nothing_is_refused():
    with pytest.raises(SystemExit, match="reports nothing"):
        _device([])


def test_two_properties_at_one_pointer_are_refused():
    """They would overwrite each other in one message, and the reading that survived would
    depend on list order — which is not a fact about anything."""
    with pytest.raises(SystemExit, match="repeats a pointer"):
        _device([MOISTURE, dict(TEMPERATURE, pointer="/value")])


def test_a_reading_is_never_retained():
    """A reading is TESTIMONY, and testimony is only true at its instant.

    The board has no clock, so a reading's timestamp is stamped by the agent at ARRIVAL — which
    is honest under exactly one assumption: delivery is immediate. A retained reading breaks it
    silently and catastrophically: an agent restarting hours later receives the broker's kept
    copy, stamps it "now", and every freshness defence — the stale detection, the ignorance
    burst, the gap — is blinded by one flag flipped in the name of reliability. Losing the
    readings published while nobody listened is a FEATURE: the burst re-fetches reality in
    minutes, where the "saved" data would be a well-preserved lie.

    Contrast the cadence command, which IS retained, correctly: a command is policy — "sleep
    30s from now on" is still true whenever the board wakes — where a reading is an event.
    Retained is right for state and wrong for testimony, and this pins the testimony half the
    way test_a_sense_request_is_never_retained pins its cousin.
    """
    device, _ = _device([MOISTURE])
    calls: list[dict] = []
    device.client.publish = lambda topic, payload, qos=0, retain=False, **kw: calls.append(
        {"topic": topic, "retain": retain})
    device._publish()
    assert calls and all(not c["retain"] for c in calls)


def test_a_scheduled_stand_in_acks_the_cadence_it_runs(monkeypatch):
    """The reading says which cadence it was taken under (#135) — the receipt for the retained
    command, and the real board's only testimony about its rhythm, since deep sleep clears its
    RAM and the retained message IS its memory."""
    device, published = _device([MOISTURE])
    device._publish()
    assert json.loads(published[-1][1])["sleep_s"] == int(device.sleep_s)


def test_a_push_stand_in_acks_nothing(monkeypatch):
    """A push device keeps its own clock and takes no orders — there is no commanded cadence to
    receipt, and a field here would invite an agent to hold a freshness rule the vocabulary
    says it may not have."""
    device, published = _device([MOISTURE], SIM_SENSE_MODE="push")
    device._publish()
    assert "sleep_s" not in json.loads(published[-1][1])


# --- the release (#152): the wake ends when the answer lands ------------------

def _command(device, doc: dict) -> None:
    """A message arriving on the device's command topic, as paho would deliver it."""
    from types import SimpleNamespace

    device._on_message(None, None, SimpleNamespace(topic=device.command_topic,
                                                   payload=json.dumps(doc).encode()))


def test_an_answer_carrying_a_cadence_releases_the_board():
    """A scheduled device publishes and then waits; the agent's reply carries `sleep_s` and IS
    the release — the sleep that follows runs on what the answer said."""
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    device._released.clear()
    _command(device, {"sleep_s": 120})
    assert device._released.is_set()
    assert device.sleep_s == 120


def test_a_sense_nudge_is_not_a_release():
    """Exactly as on the board: a nudge republishes, and what releases the wake is the answer
    to THAT reading — permission to sleep is a cadence, never a request for more."""
    device, published = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    device._released.clear()
    _command(device, {"sense": True})
    assert published, "the nudge must still republish"
    assert not device._released.is_set()


def test_a_push_device_takes_no_release_because_it_never_waits():
    """The command is discarded before the cadence branch, so nothing raises the flag — the
    same asymmetry as the ack: a device that keeps its own clock has no handshake to keep."""
    device, _ = _device([MOISTURE], SIM_SENSE_MODE="push",
                        SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    device._released.clear()
    _command(device, {"sleep_s": 120})
    assert not device._released.is_set()


# --- announce on crossing: the world holds the third clock (#151) -------------

def test_commanded_alarm_limits_arm_the_watch():
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"sleep_s": 600, "alarm": {"/value": [0.4, 0.6]}})
    assert device.alarm == {"/value": (0.4, 0.6, None)}
    assert not device._alarmed(), "0.45 sits inside the band"


def test_hand_watering_is_seen_within_the_watch_period_not_the_polling_window():
    """THE scenario the issue exists for: someone waters the plant and no agent decided it.
    The dose crosses the commanded ceiling, the watch notices, and the next publish says the
    world changed — within the watch period, not an hour later at the heartbeat."""
    device, published = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"sleep_s": 3600, "alarm": {"/value": [0.4, 0.6]}})

    device._receive(600)   # 600 ml through 2 L/fraction: 0.45 -> 0.75, past the ceiling
    assert device._alarmed(), "the watch must see the stranger's water"

    device._woke_by_alarm = True   # what the loop sets when _alarmed ends a sleep early
    device._publish()
    assert json.loads(published[-1][1]).get("wake") == "alarm", \
        "the reading must say it exists because the value moved, not because time passed"


def test_drying_out_of_the_band_is_a_crossing_too():
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"alarm": {"/value": [0.5, 1.0]}})  # 0.45 already breaches the floor
    assert device._alarmed()


def test_each_watched_channel_has_its_own_band():
    """Per channel, because which values a board can watch is a per-channel fact — and a
    temperature alarm wakes the board exactly as a moisture one does."""
    device, _ = _device([MOISTURE, TEMPERATURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"alarm": {"/value": [0.4, 0.6], "/temperature": [18.0, 24.0]}})
    assert not device._alarmed(), "0.45 and 21.0 both sit inside their bands"
    device._control({"value": 30.0, "at": "/temperature"})  # a heat spike in the room
    assert device._alarmed(), "the air leaving ITS band must wake the board too"


def test_a_device_never_given_alarm_limits_never_wakes_for_them():
    """Dormant exactly as unflashed firmware would be: no thresholds, no watch — a world whose
    device states no AlarmProcedure never sends any."""
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    device._receive(600)
    assert not device._alarmed()


def test_the_watch_reads_the_world_not_the_instrument():
    """A real ULP compares the ADC, and the grain and the spikes are properties of the REPORT:
    a board that woke for its own measurement noise would cry wolf at its own echo."""
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd",
                        SIM_SPIKE_CHANCE="1", SIM_SPIKE_SPAN="0.5")
    _command(device, {"alarm": {"/value": [0.2, 0.9]}})
    assert not device._alarmed(), "spikes are report-side and must not trip the watch"


def test_a_push_sentinel_holds_alarm_limits_baked_at_flash():
    """The second firmware's stand-in: a push device takes no orders, so its band arrives as
    SIM_ALARM — its config.h — and a crossing makes it speak off its own tick, marked as the
    news it is. No sleep_s either way: nothing commands this board, so there is nothing to
    receipt."""
    device, published = _device([MOISTURE], SIM_SENSE_MODE="push",
                                SIM_ALARM='{"/value": [0.4, 0.6]}')
    assert device.alarm == {"/value": (0.4, 0.6, None)}
    device._receive(600)   # a stranger's watering: 0.45 -> 0.75, past the ceiling
    assert device._alarmed(), "the sentinel must see the water"
    device._woke_by_alarm = True
    device._publish()
    doc = json.loads(published[-1][1])
    assert doc.get("wake") == "alarm"
    assert "sleep_s" not in doc


def test_a_scheduled_device_ignores_baked_alarm_limits():
    """SIM_ALARM is the sentinel's config.h; a governed device is COMMANDED its band, and
    reading both would let the two sources disagree about one watch."""
    device, _ = _device([MOISTURE], SIM_ALARM='{"/value": [0.4, 0.6]}')
    assert device.alarm == {}


def test_a_jolt_inside_the_band_is_an_alarm_too():
    """The deviation half (#151's 'configurable delta'): a stranger waters a COMFORTABLE pot —
    0.45 to 0.55 never leaves the band, and the move itself is the news. Process control calls
    this the deviation alarm, and it rides the same watch as the HI/LO one."""
    device, published = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"sleep_s": 3600, "alarm": {"/value": [0.2, 0.9, 0.05]}})
    device._publish()                       # the report the deviation measures from (0.45)
    assert not device._alarmed(), "nothing has moved yet"
    device._receive(200)                    # +0.10: well inside the band, twice the delta
    assert device._alarmed(), "an in-band jolt past the delta must wake the board"


def test_slow_drift_inside_the_band_stays_silent():
    """The other half of the same limit: ordinary drying between heartbeats moves less than
    the delta, and a deviation alarm that woke for it would just be a second heartbeat."""
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"alarm": {"/value": [0.2, 0.9, 0.05]}})
    device._publish()
    device.values[0].value -= 0.02          # a heartbeat's worth of drying
    assert not device._alarmed()


# --- the news must survive two looks (#180) -----------------------------------

def test_one_breaching_look_is_a_glitch_not_news():
    """The persistence counter, mirrored from the boards' ULP: a breach visible in exactly
    one look never wakes the radio — the same argument that derived the watch period, one
    step further. The stand-in has no ADC to glitch, so for it this is pure rehearsed
    latency; the rehearsal is the point."""
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"sleep_s": 3600, "alarm": {"/value": [0.4, 0.6]}})
    device._receive(600)   # 0.45 -> 0.75, past the ceiling — and it stays there
    assert not device._news(), "the first breaching look is not yet news"
    assert device._news(), "the second consecutive look is — the world stayed changed"
    assert not device._news(), "and the count starts over once the news is out"


def test_an_in_window_look_resets_the_vigil():
    device, _ = _device([MOISTURE], SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    _command(device, {"sleep_s": 3600, "alarm": {"/value": [0.4, 0.6]}})
    device._receive(600)                      # breach: 0.75
    assert not device._news()                 # one look so far
    device.values[0].value = 0.5              # the spike passed; back in the window
    assert not device._news()                 # the vigil starts over
    device._receive(600)                      # a second, separate excursion
    assert not device._news(), "its first look counts from one, not from two"


def test_the_persistence_figure_is_config_like_everything_else():
    device, _ = _device([MOISTURE], SIM_ALARM_PERSIST_LOOKS="3",
                        SIM_COMMAND_TOPIC="sensors/board_x/cmd")
    assert device.alarm_persist == 3


# --- the barrel learns to run dry (arc 1) -------------------------------------

def test_a_source_drains_by_what_its_valves_dispense():
    """The sign of the conversion is which side of the wire a value is on: the same 500 ml
    that raises a pot's fraction lowers the source's level by half a litre. Clamped at dry —
    a barrel cannot owe water."""
    device, published = _device([{"pointer": "/value", "min": 0.0, "max": 5.0,
                                  "initial": 3.0, "litres": -1.0}])
    device._receive(500)
    assert device.values[0].value == pytest.approx(2.5)
    device._receive(4000)
    assert device.values[0].value == 0.0, "a barrel cannot owe water"


def test_a_source_hears_every_valve_that_draws_from_it(monkeypatch):
    """SIM_DOSE_TOPIC is a comma-joined set now: a pot takes water on one channel, a source
    loses it on several — and every one of them must actually be SUBSCRIBED, which the first
    bench run of the barrel found was not true: the parse learned the plural and the
    subscribe still read the singular, so the level never drained and the crash said so."""
    device, _ = _device([MOISTURE],
                        SIM_DOSE_TOPIC="actuators/a/status,actuators/b/status")
    assert device.dose_topics == {"actuators/a/status", "actuators/b/status"}

    class Subs:
        def __init__(self): self.topics = []
        def subscribe(self, t): self.topics.append(t)
    subs = Subs()
    device._on_connect(subs, None, None, 0, None)
    assert {"actuators/a/status", "actuators/b/status"} <= set(subs.topics)

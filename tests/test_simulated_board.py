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
               **env}
    published: list[tuple[str, str]] = []
    with pytest.MonkeyPatch.context() as mp:
        for k, v in environ.items():
            mp.setenv(k, v)
        device = sim.SimulatedSensor()
    device.client.publish = lambda topic, payload, qos=0: published.append((topic, payload))
    return device, published


MOISTURE = {"pointer": "/value", "min": 0.0, "max": 1.0, "initial": 0.45,
            "drift": 0.02, "litres": 2.0}
TEMPERATURE = {"pointer": "/temperature", "min": -10.0, "max": 45.0,
               "initial": 21.0, "drift": -0.05}


def test_one_message_carries_every_property_the_board_reports():
    """One message and not one per value, because that is what a board does: it wakes once,
    reads what it is wired to, and spends one transmission on the lot."""
    device, published = _device([MOISTURE, TEMPERATURE])
    device._publish()

    assert len(published) == 1, "a board sends one message, however many things it read"
    topic, payload = published[0]
    assert topic == "sensors/board_x/reading"
    assert json.loads(payload) == {"sensor": "board_x", "value": 0.45, "temperature": 21.0}


def test_a_single_property_board_sends_exactly_what_it_always_did():
    """The shape a probe has always published. A list of one is not a special case."""
    device, published = _device([MOISTURE])
    device._publish()
    assert json.loads(published[0][1]) == {"sensor": "board_x", "value": 0.45}


def test_each_value_drifts_in_its_own_direction_and_range():
    """0..1 was never a fact about sensing, only about soil moisture. A room warms while a pot
    dries, and both are clamped by what their own model says they can report."""
    device, _ = _device([MOISTURE, TEMPERATURE])
    for _ in range(3):
        device._dry()
    by_pointer = {v.pointer: v.value for v in device.values}
    assert by_pointer["/value"] == pytest.approx(0.45 - 3 * 0.02)
    assert by_pointer["/temperature"] == pytest.approx(21.0 + 3 * 0.05)


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

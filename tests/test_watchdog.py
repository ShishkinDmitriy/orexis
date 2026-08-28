"""The agent notices it is cut off, and resigns rather than endures (#53).

The incident this answers: a session that died and never came back, inside a container that
looked healthy for two days. Every check here is about telling that apart from its lookalikes —
a flapping link that recovers, a quiet-but-connected agent, a board that simply sleeps long.
"""

from __future__ import annotations

import logging
import time
from types import SimpleNamespace

import pytest

from conftest import build_agent, genesis_store, wired_sensors


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_store(), monkeypatch)


def resignations(agent) -> list[str]:
    """Capture instead of SIGTERM — the test process would rather not stop itself."""
    said: list[str] = []
    agent.module("mqtt").watchdog._resign = lambda why: said.append(why)
    return said


def test_the_bound_comes_from_the_ontology_not_the_code(fern):
    assert fern.module("mqtt").watchdog.resign_after_s == 600


def test_a_connected_agent_is_left_alone(fern):
    said = resignations(fern)
    fern.module("mqtt")._on_connect()
    fern.module("mqtt").watchdog.check()
    assert said == []


def test_cut_off_past_the_bound_is_a_resignation(fern):
    """Born disconnected and never connected counts too, deliberately: an agent whose CONNACK
    is refused in a loop is exactly as cut off as one whose session died."""
    said = resignations(fern)
    fern.module("mqtt").disconnected_at = time.monotonic() - 601
    fern.module("mqtt").watchdog.check()
    assert len(said) == 1 and "cut off from the bus" in said[0]


def test_a_short_outage_is_endured(fern):
    said = resignations(fern)
    fern.module("mqtt").disconnected_at = time.monotonic() - 30
    fern.module("mqtt").watchdog.check()
    assert said == []


def test_one_reconnect_resets_the_clock_so_flapping_never_accumulates(fern):
    fern.module("mqtt")._on_disconnect(0)
    assert fern.module("mqtt").disconnected_for_s() is not None
    fern.module("mqtt")._on_connect()
    assert fern.module("mqtt").disconnected_for_s() is None
    # and a repeated notice of one dead session is the same outage, not a fresh clock
    fern.module("mqtt")._on_disconnect(0)
    first = fern.module("mqtt").disconnected_at
    fern.module("mqtt")._on_disconnect(0)
    assert fern.module("mqtt").disconnected_at == first


def test_a_dead_network_thread_is_a_resignation_whatever_the_flag_says(fern):
    """The connected flag is set by a callback, and a dead loop thread fires no callbacks —
    so the corpse is checked before the flag is believed."""
    said = resignations(fern)
    fern.module("mqtt")._on_connect()  # the stale-true flag of the incident
    fern.module("mqtt").client._thread = SimpleNamespace(is_alive=lambda: False)
    fern.module("mqtt").watchdog.check()
    assert len(said) == 1 and "network thread is dead" in said[0]


def test_a_live_thread_is_not_a_corpse(fern):
    said = resignations(fern)
    fern.module("mqtt")._on_connect()
    fern.module("mqtt").client._thread = SimpleNamespace(is_alive=lambda: True)
    fern.module("mqtt").watchdog.check()
    assert said == []


def _quiet_module(lines):
    """A module answering the `quiet` extension point with whatever `lines` currently holds."""
    return SimpleNamespace(
        quiet=lambda: list(lines),
        answer=lambda term: (lambda: list(lines)) if term.endswith("#quiet") else None)


def test_what_went_quiet_is_said_once_and_recovery_is_said_too(fern, caplog):
    """A lamp that repeats itself is one you stop reading: entry once, recovery once,
    and the ticks in between are silent."""
    fern.module("mqtt")._on_connect()
    lines = [("moisture_sensor_fern",
              "moisture_sensor_fern: nothing for 700s, past the 645s I allow")]
    fern.modules.append(_quiet_module(lines))

    with caplog.at_level(logging.INFO, logger="watchdog"):
        fern.module("mqtt").watchdog.check()
        assert sum("nothing for 700s" in r.message for r in caplog.records) == 1
        fern.module("mqtt").watchdog.check()
        assert sum("nothing for 700s" in r.message for r in caplog.records) == 1

        lines.clear()
        fern.module("mqtt").watchdog.check()
    recovered = [r for r in caplog.records if "heard again" in r.message]
    assert len(recovered) == 1


def test_a_silence_that_goes_on_is_still_ONE_silence(fern, caplog):
    """The line carries the elapsed seconds and so changes on every look. The fault does not.

    THE TEST ABOVE HELD THE LINE CONSTANT and therefore passed for as long as the bug lived:
    the watchdog differenced the LINES, so a growing age read as a fresh fault plus a recovery
    on every single tick. On the bench that was `nothing for 337s` beside `heard again — was:
    nothing for 277s`, once a minute, while nothing had been heard for seven minutes. Anyone
    alerting on the recovery line was told the sensor came back sixty times over.
    """
    fern.module("mqtt")._on_connect()
    lines = [("moisture_sensor_fern", "moisture_sensor_fern: nothing for 100s, past the 55s I allow")]
    fern.modules.append(_quiet_module(lines))

    with caplog.at_level(logging.INFO, logger="watchdog"):
        for age in (100, 160, 220, 280):
            lines[:] = [("moisture_sensor_fern",
                         f"moisture_sensor_fern: nothing for {age}s, past the 55s I allow")]
            fern.module("mqtt").watchdog.check()

        assert [r for r in caplog.records if "heard again" in r.message] == [], (
            "an unbroken silence claimed to have recovered")
        assert sum("nothing for" in r.message for r in caplog.records) == 1, (
            "one fault, said once, however the line renders")

        #  And it must still notice the real recovery when it comes.
        lines.clear()
        fern.module("mqtt").watchdog.check()
    assert len([r for r in caplog.records if "heard again" in r.message]) == 1


def test_two_sensors_going_quiet_are_two_lines(fern, caplog):
    """Keyed, not counted: the second silence is its own entry and its own recovery."""
    fern.module("mqtt")._on_connect()
    lines = [("a", "a: nothing for 100s, past the 55s I allow")]
    fern.modules.append(_quiet_module(lines))

    with caplog.at_level(logging.INFO, logger="watchdog"):
        fern.module("mqtt").watchdog.check()
        lines.append(("b", "b: nothing for 90s, past the 55s I allow"))
        fern.module("mqtt").watchdog.check()
        assert sum("nothing for" in r.message for r in caplog.records) == 2

        lines[:] = [("b", "b: nothing for 150s, past the 55s I allow")]   # a came back, b did not
        fern.module("mqtt").watchdog.check()
    recovered = [r for r in caplog.records if "heard again" in r.message]
    assert len(recovered) == 1 and "a:" in recovered[0].message


def test_a_quiet_sensor_is_reported_by_sensing(fern):
    """The module's own half: delivered once, then silent past the freshness rule. The limit
    is the same `stale_after_s` the rule uses, so the log and the refusal cannot disagree."""
    sensor = next(s for s in wired_sensors(fern) if s.observes.endswith("SoilMoisture"))
    fern.deliver(sensor.reading_topic, {"moisture": 0.5})
    p = fern.subscribing()
    assert p.quiet() == []
    p.observations.last_reading_at[sensor.local_id] = (
        time.monotonic() - p.stale_after_s(sensor.subject, sensor.observes) - 60)
    overdue = p.quiet()
    assert len(overdue) == 1 and sensor.local_id in overdue[0]


def test_a_sensor_that_never_delivered_is_not_called_quiet(fern):
    """Different fault, different voice: readings_total at zero says it, and an age invented
    for it would claim a reading that never happened."""
    assert fern.subscribing().quiet() == []

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

from conftest import build_agent, genesis_store


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_store(), monkeypatch)


def resignations(agent) -> list[str]:
    """Capture instead of SIGTERM — the test process would rather not stop itself."""
    said: list[str] = []
    agent.watchdog._resign = lambda why: said.append(why)
    return said


def test_the_bound_comes_from_the_ontology_not_the_code(fern):
    assert fern.watchdog.resign_after_s == 600


def test_a_connected_agent_is_left_alone(fern):
    said = resignations(fern)
    fern.metrics.connected()
    fern.watchdog.check()
    assert said == []


def test_cut_off_past_the_bound_is_a_resignation(fern):
    """Born disconnected and never connected counts too, deliberately: an agent whose CONNACK
    is refused in a loop is exactly as cut off as one whose session died."""
    said = resignations(fern)
    fern.metrics.disconnected_at = time.monotonic() - 601
    fern.watchdog.check()
    assert len(said) == 1 and "cut off from the bus" in said[0]


def test_a_short_outage_is_endured(fern):
    said = resignations(fern)
    fern.metrics.disconnected_at = time.monotonic() - 30
    fern.watchdog.check()
    assert said == []


def test_one_reconnect_resets_the_clock_so_flapping_never_accumulates(fern):
    fern.metrics.disconnected()
    assert fern.metrics.disconnected_for_s() is not None
    fern.metrics.connected()
    assert fern.metrics.disconnected_for_s() is None
    # and a repeated notice of one dead session is the same outage, not a fresh clock
    fern.metrics.disconnected()
    first = fern.metrics.disconnected_at
    fern.metrics.disconnected()
    assert fern.metrics.disconnected_at == first


def test_a_dead_network_thread_is_a_resignation_whatever_the_flag_says(fern):
    """The connected flag is set by a callback, and a dead loop thread fires no callbacks —
    so the corpse is checked before the flag is believed."""
    said = resignations(fern)
    fern.metrics.connected()  # the stale-true flag of the incident
    fern.mqtt._thread = SimpleNamespace(is_alive=lambda: False)
    fern.watchdog.check()
    assert len(said) == 1 and "network thread is dead" in said[0]


def test_a_live_thread_is_not_a_corpse(fern):
    said = resignations(fern)
    fern.metrics.connected()
    fern.mqtt._thread = SimpleNamespace(is_alive=lambda: True)
    fern.watchdog.check()
    assert said == []


def test_what_went_quiet_is_said_once_and_recovery_is_said_too(fern, caplog):
    """A lamp that repeats itself is one you stop reading: entry once, recovery once,
    and the ticks in between are silent."""
    fern.metrics.connected()
    lines = ["moisture_sensor_fern: nothing for 700s, past the 645s I allow"]
    fern.modules.append(SimpleNamespace(quiet=lambda: list(lines)))

    with caplog.at_level(logging.INFO, logger="watchdog"):
        fern.watchdog.check()
        assert sum("nothing for 700s" in r.message for r in caplog.records) == 1
        fern.watchdog.check()
        assert sum("nothing for 700s" in r.message for r in caplog.records) == 1

        lines.clear()
        fern.watchdog.check()
    recovered = [r for r in caplog.records if "heard again" in r.message]
    assert len(recovered) == 1


def test_a_quiet_sensor_is_reported_by_perception(fern):
    """The module's own half: delivered once, then silent past the freshness rule. The limit
    is the same `stale_after_s` the rule uses, so the log and the refusal cannot disagree."""
    sensor = next(s for s in fern.me.sensors if s.observes.endswith("SoilMoisture"))
    fern.deliver(sensor.reading_topic, {"value": 0.5})
    p = fern.subscribing()
    assert p.quiet() == []
    fern.metrics.last_reading_at[sensor.local_id] = (
        time.monotonic() - p.stale_after_s(sensor.subject, sensor.observes) - 60)
    overdue = p.quiet()
    assert len(overdue) == 1 and sensor.local_id in overdue[0]


def test_a_sensor_that_never_delivered_is_not_called_quiet(fern):
    """Different fault, different voice: readings_total at zero says it, and an age invented
    for it would claim a reading that never happened."""
    assert fern.subscribing().quiet() == []

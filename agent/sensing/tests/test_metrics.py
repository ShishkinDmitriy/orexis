"""Sensing's metrics: the silence counted in the belief base, and each reading's interval tallied
as `received` writes it — against the probe the other sensing suites stand in."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock, metrics
from agent.sensing.metrics import gauges, made_before
from agent.sensing.missed import SILENT_AFTER, missed
from agent.sensing.received import received
from agent.series import METRICS, Sink, install

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
PROBE = "http://example.org/test#probe"
CADENCE = timedelta(seconds=900)


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    received(store, snapshots.ME, PROBE, b'{"value": 0.2}', snapshots.NOW)
    return store


@pytest.fixture
def written():
    out = []
    install(METRICS, Sink(METRICS, "m", lambda bucket, record: out.extend(record)))
    yield out
    install(METRICS, None)
    metrics.reset()


def test_the_silence_is_counted_in_the_belief_base(pot, snapshots):
    """None while the reading stands, one once the probe is past its limit of cadences."""
    silence = lambda: {g.name: f for g, f in gauges(pot)}["silence"]
    assert silence() == {"silent": 0}
    missed(pot, snapshots.ME, snapshots.NOW + CADENCE * (1 + SILENT_AFTER))
    assert silence() == {"silent": 1}


def test_a_reading_replacing_one_is_tallied_with_its_interval_and_the_cadence(pot, snapshots, written):
    """Read before the old reading goes, so the interval is between the two: here a cadence and a
    half, beside the cadence the world states, tagged by the sensor."""
    assert made_before(pot, "urn:no:such:graph") is None
    received(pot, snapshots.ME, PROBE, b'{"value": 0.3}', snapshots.NOW + CADENCE * 1.5)
    (point,) = metrics.flush()
    assert point["measurement"] == "received" and point["fields"]["count"] == 1
    assert point["fields"]["interval_s_max"] == 1350.0 and point["fields"]["cadence_s_max"] == 900.0
    assert set(point["tags"]) == {"sensor"}

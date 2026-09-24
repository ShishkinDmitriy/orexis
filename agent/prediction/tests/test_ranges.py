"""The ranges that apply to what a sensor observes, in SSN-System's words, read by the crossing
as their two numbers: its host's, its host's subject's where the host is a sample, and its own."""

from __future__ import annotations

from pathlib import Path

from agent.prediction.ranges import ranges_of, side
from agent.store import update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"

#  The probe's own operating range, the pot's survival range, the pot's operating range.
BOUNDS = [(0.0, 1.0), (0.02, 0.45), (0.1, 0.3)]


def test_the_hosts_and_the_sensors_own_bounds_for_the_property(snapshots):
    store = snapshots.stand_in(WORLD)
    assert ranges_of(store, PROBE, TEST + "moisture") == BOUNDS
    assert ranges_of(store, PROBE, TEST + "warmth") == []
    assert ranges_of(store, TEST + "nobody", TEST + "moisture") == []


def test_a_sensor_in_a_sample_gets_the_subjects_ranges(snapshots):
    store = snapshots.stand_in(WORLD)
    update(store, """PREFIX : <http://example.org/test#>
DELETE DATA { GRAPH :world { :probe sosa:isHostedBy :zz } } ;
INSERT DATA { GRAPH :world { :patch a sosa:Sample ; sosa:isSampleOf :zz . :probe sosa:isHostedBy :patch } }""")
    assert ranges_of(store, PROBE, TEST + "moisture") == BOUNDS


def test_a_side_is_inclusive_at_the_bounds():
    assert [side(0.1, 0.3, v) for v in (0.05, 0.1, 0.2, 0.3, 0.31)] == [-1, 0, 0, 0, 1]

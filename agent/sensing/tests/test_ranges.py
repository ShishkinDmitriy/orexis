"""The ranges that apply to what a sensor observes, in SSN-System's words, read by the crossing:
its host's, its host's subject's where the host is a sample, and its own."""

from __future__ import annotations

from pathlib import Path

from agent.sensing.ranges import Range, ranges_of
from agent.store import update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
TEST = "http://example.org/test#"


def test_the_hosts_and_the_sensors_own_ranges_for_the_property(snapshots):
    store = snapshots.stand_in(WORLD)
    found = {r.uri.rsplit("#", 1)[-1]: r for r in ranges_of(store, TEST + "probe", TEST + "moisture")}
    assert set(found) == {"zz.operating", "zz.survival", "probe.operating"}
    assert (found["zz.operating"].low, found["zz.operating"].high) == (0.1, 0.3)
    assert found["zz.survival"].kind.endswith("SurvivalRange") and found["probe.operating"].kind.endswith("OperatingRange")
    assert ranges_of(store, TEST + "probe", TEST + "warmth") == []
    assert ranges_of(store, TEST + "nobody", TEST + "moisture") == []


def test_a_sensor_in_a_sample_gets_the_subjects_ranges(snapshots):
    store = snapshots.stand_in(WORLD)
    update(store, """PREFIX : <http://example.org/test#>
DELETE DATA { GRAPH :world { :probe sosa:isHostedBy :zz } } ;
INSERT DATA { GRAPH :world { :patch a sosa:Sample ; sosa:isSampleOf :zz . :probe sosa:isHostedBy :patch } }""")
    found = {r.uri.rsplit("#", 1)[-1] for r in ranges_of(store, TEST + "probe", TEST + "moisture")}
    assert found == {"zz.operating", "zz.survival", "probe.operating"}


def test_a_side_is_inclusive_at_the_bounds():
    r = Range(TEST + "r", "operating", 0.1, 0.3)
    assert [r.side(v) for v in (0.05, 0.1, 0.2, 0.3, 0.31)] == [-1, 0, 0, 0, 1]

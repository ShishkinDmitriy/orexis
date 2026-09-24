"""The ranges a subject states for a property, in SSN-System's words, read by the crossing."""

from __future__ import annotations

from pathlib import Path

from agent.sensing.ranges import Range, ranges_of

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
TEST = "http://example.org/test#"


def test_the_subjects_and_the_instruments_ranges_for_the_property(snapshots):
    store = snapshots.stand_in(WORLD)
    found = {r.uri.rsplit("#", 1)[-1]: r for r in ranges_of(store, TEST + "zz", TEST + "moisture")}
    assert set(found) == {"zz.operating", "zz.survival", "probe.operating"}
    assert (found["zz.operating"].low, found["zz.operating"].high) == (0.1, 0.3)
    assert found["zz.survival"].kind.endswith("SurvivalRange") and found["probe.operating"].kind.endswith("OperatingRange")
    assert ranges_of(store, TEST + "zz", TEST + "warmth") == []


def test_a_side_is_inclusive_at_the_bounds():
    r = Range(TEST + "r", "operating", 0.1, 0.3)
    assert [r.side(v) for v in (0.05, 0.1, 0.2, 0.3, 0.31)] == [-1, 0, 0, 0, 1]

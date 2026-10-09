"""The ranges that apply to what a sensor observes, in SSN-System's words, read by the crossing
as their two numbers: its host's, its host's subject's where the host is a sample, and its own."""

from __future__ import annotations

from pathlib import Path

from agent.prediction.ranges import ranges_of, side

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
    """The probe mounted in a patch of the pot reaches the pot's ranges through the sample."""
    store = snapshots.stand_in(Path(__file__).parent / "worlds" / "a_probe_in_a_patch.trig")
    assert ranges_of(store, PROBE, TEST + "moisture") == BOUNDS


def test_a_narrower_range_is_answered_beside_the_others(snapshots):
    """#944: a range the pot states inside its operating range, `orexis:hasNarrowerRange`, is answered
    with the rest, so a crossing of its bounds is placed as theirs are and no stretch straddles one."""
    from agent.store import NAMESPACES

    store = snapshots.stand_in(WORLD)
    store.update(f"""INSERT DATA {{ GRAPH <{TEST}world> {{
      <{TEST}zamioculcas> orexis:hasNarrowerRange <{TEST}zamioculcas.narrower> .
      <{TEST}zamioculcas.narrower> ssn-system:inCondition
          [ ssn:forProperty <{TEST}moisture> ; schema:minValue 0.12 ; schema:maxValue 0.28 ] }} }}""", prefixes=NAMESPACES)
    assert ranges_of(store, PROBE, TEST + "moisture") == sorted([*BOUNDS, (0.12, 0.28)])


def test_a_side_is_inclusive_at_the_bounds():
    assert [side(0.1, 0.3, v) for v in (0.05, 0.1, 0.2, 0.3, 0.31)] == [-1, 0, 0, 0, 1]

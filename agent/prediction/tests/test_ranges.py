"""The ranges that apply to what a sensor observes, in SSN-System's words, read by the crossing
as their two numbers, their margin and their name: its host's, its host's subject's where the host
is a sample, and its own."""

from __future__ import annotations

from pathlib import Path

from agent.prediction.ranges import Range, cleared, ranges_of, side

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"

#  The probe's own operating range, the pot's survival range, the pot's operating range — none
#  stating a margin.
BOUNDS = [Range(TEST + "probe.operating", 0.0, 1.0, 0.0), Range(TEST + "zamioculcas.survival", 0.02, 0.45, 0.0),
          Range(TEST + "zamioculcas.operating", 0.1, 0.3, 0.0)]


def test_the_hosts_and_the_sensors_own_bounds_for_the_property(snapshots):
    store = snapshots.stand_in(WORLD)
    assert ranges_of(store, PROBE, TEST + "moisture") == BOUNDS
    assert ranges_of(store, PROBE, TEST + "warmth") == []
    assert ranges_of(store, TEST + "nobody", TEST + "moisture") == []


def test_a_sensor_in_a_sample_gets_the_subjects_ranges(snapshots):
    """The probe mounted in a patch of the pot reaches the pot's ranges through the sample."""
    store = snapshots.stand_in(Path(__file__).parent / "worlds" / "a_probe_in_a_patch.trig")
    assert ranges_of(store, PROBE, TEST + "moisture") == BOUNDS


def test_a_range_answers_the_margin_its_condition_states(snapshots):
    """`orexis:margin` on the pot's operating condition is answered beside its bounds; the ranges
    stating none answer nought."""
    store = snapshots.stand_in(WORLD)
    store.update("INSERT { GRAPH ?g { ?c <http://example.org/orexis#margin> 0.01 } } WHERE { GRAPH ?g { "
                 "<http://example.org/test#zamioculcas.operating> <http://www.w3.org/ns/ssn/systems/inCondition> ?c } }")
    assert ranges_of(store, PROBE, TEST + "moisture") == [*BOUNDS[:2], BOUNDS[2]._replace(margin=0.01)]


def test_a_blank_range_is_answered_nameless_and_its_margin_nought(snapshots):
    """No side can be carried for a range with no name, so the rules judge it bare and the crossing
    must too, whatever margin it states."""
    store = snapshots.stand_in(WORLD, WORLD.read_text().replace(
        ":zamioculcas.operating ssn-system:inCondition [ schema:maxValue 0.3 ;",
        ":zamioculcas ssn-system:hasOperatingRange [ ssn-system:inCondition [ orexis:margin 0.01 ; schema:maxValue 0.25 ;")
        .replace("schema:minValue 0.1 ; ssn:forProperty :moisture ] .", "schema:minValue 0.1 ; ssn:forProperty :moisture ] ] ."))
    assert Range(None, 0.1, 0.25, 0.0) in ranges_of(store, PROBE, TEST + "moisture")


def test_a_side_is_inclusive_at_the_bounds():
    assert [side(0.1, 0.3, v) for v in (0.05, 0.1, 0.2, 0.3, 0.31)] == [-1, 0, 0, 0, 1]


def test_a_margin_holds_a_side_only_for_a_reading_coming_from_beyond_the_bound():
    """Floor 0.30, margin 0.0002: coming from inside, 0.2999 is below and 0.3001 inside; coming from
    below, 0.3001 is still below and 0.3002 clears; at the ceiling, the mirror."""
    assert [side(0.30, 0.60, v, 0.0002, 0) for v in (0.2999, 0.3001, 0.5999, 0.6001)] == [-1, 0, 0, 1]
    assert [side(0.30, 0.60, v, 0.0002, -1) for v in (0.2999, 0.3001, 0.30019, 0.3002)] == [-1, -1, -1, 0]
    assert [side(0.30, 0.60, v, 0.0002, 1) for v in (0.6001, 0.5999, 0.59981, 0.5998)] == [1, 1, 1, 0]
    assert side(0.30, 0.60, 0.2999, 0.0002, 1) == -1, "a reading under the floor is below whatever it came from"
    assert [side(0.30, 0.60, v, 0.0, -1) for v in (0.2999, 0.30, 0.3001)] == [-1, 0, 0], "no margin, no memory"


def test_a_bound_cleared_is_the_decimal_the_rules_reach():
    """0.1 + 0.2 is a hair over 0.3 in floats, so a reading written 0.3 coming from below a floor of
    0.1 with a margin of 0.2 would read short of it and stay below, where the rules, adding decimals,
    say it has cleared; the bound cleared is the decimal."""
    assert 0.1 + 0.2 != 0.3 and 0.3 + 0.0002 != 0.3002, "the hazard this guards stopped being one"
    assert cleared(0.1, 0.2) == 0.3 and cleared(0.3, 0.0002) == 0.3002 and cleared(24.0, -0.02) == 23.98
    assert side(0.1, 0.6, 0.3, 0.2, -1) == 0, "cleared, as the rules judge it"

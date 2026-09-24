"""How often a sensor reports, read off SSN-System's frequency in the unit the world states —
over the pot's probe and over a board whose peripherals each state theirs in a unit of their own."""

from __future__ import annotations

from pathlib import Path

from agent.sensing.cadence import cadence_of

WORLDS = Path(__file__).parent / "worlds"
POT = WORLDS / "a_pot_and_its_probe.trig"
BOARD = WORLDS / "a_board_and_its_peripherals.trig"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"


def test_the_pots_probe_reports_every_quarter_hour(snapshots):
    assert cadence_of(snapshots.stand_in(POT), PROBE) == 900.0


def test_each_peripheral_reports_as_its_frequency_says_in_its_own_unit(snapshots):
    store = snapshots.stand_in(BOARD)
    assert cadence_of(store, TEST + "thermo") == 120.0, "two of QUDT's minutes"
    assert cadence_of(store, TEST + "hygro") == 3600.0, "one hour by its UN/CEFACT code"
    assert cadence_of(store, TEST + "gauge") == 30.0, "no unit is seconds"


def test_no_frequency_or_a_unit_nothing_converts_is_no_cadence(snapshots, caplog):
    store = snapshots.stand_in(BOARD)
    assert cadence_of(store, PROBE) is None, "the board's probe states no frequency"
    assert cadence_of(store, TEST + "nobody") is None
    with caplog.at_level("WARNING", logger="cadence"):
        assert cadence_of(store, TEST + "barometer") is None
    assert "nothing here converts" in caplog.text

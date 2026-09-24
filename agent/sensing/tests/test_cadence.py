"""How often a sensor reports, read off SSN-System's frequency in the unit the world states."""

from __future__ import annotations

from pathlib import Path

from agent.sensing.cadence import cadence_of
from agent.store import update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"


def _restated(store, value: str, unit: str | None):
    update(store, "PREFIX : <http://example.org/test#>\nPREFIX unit: <http://qudt.org/vocab/unit/>\n"
           "DELETE WHERE { GRAPH ?g { ?probe ssn-system:hasSystemCapability ?c } } ;\n"
           "INSERT DATA { GRAPH :world { :probe ssn-system:hasSystemCapability [ ssn-system:hasSystemProperty "
           f"[ a ssn-system:Frequency ; schema:value {value} {'; schema:unitCode ' + unit if unit else ''} ] ] }} }}")


def test_the_probe_reports_every_quarter_hour(snapshots):
    assert cadence_of(snapshots.stand_in(WORLD), PROBE) == 900.0


def test_a_unit_is_converted_and_none_means_seconds(snapshots):
    store = snapshots.stand_in(WORLD)
    _restated(store, "2", "unit:MIN")
    assert cadence_of(store, PROBE) == 120.0
    _restated(store, "1", '"HUR"')
    assert cadence_of(store, PROBE) == 3600.0
    _restated(store, "30", None)
    assert cadence_of(store, PROBE) == 30.0


def test_no_frequency_or_a_unit_nothing_converts_is_no_cadence(snapshots, caplog):
    store = snapshots.stand_in(WORLD)
    assert cadence_of(store, TEST + "nobody") is None
    _restated(store, "1", "unit:FortNight")
    with caplog.at_level("WARNING", logger="cadence"):
        assert cadence_of(store, PROBE) is None
    assert "nothing here converts" in caplog.text

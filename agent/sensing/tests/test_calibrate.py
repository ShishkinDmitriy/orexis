"""Telling the agent what a sensor reads now: the calibration point it names takes the number the
latest observation holds, or the one the teller says, and the next reading is concluded through it —
over the pot's probe, publishing its raw count, which the agent believes two points of."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import PUBLIC
from agent.sensing.calibrate import _main, calibrate
from agent.sensing.ontology import CALIBRATION_GRAPH
from agent.sensing.received import received
from agent.store import document, entry, graphs_of, put_document, rows, update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
RULES = Path(__file__).parents[1] / "rules.ttl"
T = "http://example.org/test#"
PROBE = T + "probe"
_POINTS_Q = """SELECT ?label ?raw WHERE { GRAPH ?g { ?s sensing:calibrationPoint ?p . ?p rdfs:label ?label ; sensing:raw ?raw } }"""


@pytest.fixture
def pot(monkeypatch, snapshots):
    """The pot's probe publishing its raw count, believed to read 3200 dry and 1300 wet, and one
    reading of 2250 written."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(RULES))
    update(store, f"""PREFIX sensing: <http://example.org/orexis/sensing#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{
  GRAPH <{T}binding> {{ <{PROBE}> sensing:readingPointer "/raw" }}
  GRAPH <{T}calibration> {{
    <{PROBE}> sensing:calibrationPoint [ rdfs:label "dry" ; sensing:raw 3200 ; sensing:quantity 0.0 ] ,
                                       [ rdfs:label "wet" ; sensing:raw 1300 ; sensing:quantity 1.0 ] }}
  {entry(store, T + "binding", "http://example.org/orexis#PublicGraph", "http://example.org/orexis#Asserted")}
  {entry(store, T + "calibration", CALIBRATION_GRAPH, "http://example.org/orexis#Asserted")}
  {entry(store, T + "calibration", "http://example.org/orexis#PublicGraph", "http://example.org/orexis#Asserted")} }}""")
    return store


def _read(store, snapshots, raw: int) -> float:
    """A reading of `raw`, written and revised as the deliberator revises it, and the moisture concluded."""
    (graph,) = received(store, snapshots.ME, PROBE, f'{{"raw": {raw}}}'.encode(), snapshots.NOW)
    revise(store, graph, read=graphs_of(store, PUBLIC))
    (said,) = rows(store, "SELECT ?q WHERE { ?o sosa:hasSimpleResult ?q }", [graph, graph + "/revisions"])
    return float(said["q"])


def _points(store) -> dict[str, float]:
    return {r["label"]: float(r["raw"]) for r in rows(store, _POINTS_Q, ())}


def test_the_rule_concludes_the_moisture_through_the_two_points(pot, snapshots):
    """Halfway between dry and wet is half, and water past the wet point reads past one, unclamped."""
    assert _read(pot, snapshots, 2250) == 0.5
    assert _read(pot, snapshots, 1110) == 1.1


def test_told_the_probe_is_dry_now_the_dry_point_takes_what_it_reads(pot, snapshots):
    """The probe in dry air reads 2250, so that is dry now; a reading of 2250 is nought after."""
    _read(pot, snapshots, 2250)
    assert calibrate(pot, PROBE, "dry") == T + "calibration"
    assert _points(pot) == {"dry": 2250.0, "wet": 1300.0}
    assert _read(pot, snapshots, 2250) == 0.0


def test_a_number_the_teller_says_outranks_the_reading(pot):
    calibrate(pot, PROBE, "wet", raw=1105)
    assert _points(pot)["wet"] == 1105.0


def test_a_point_the_agent_does_not_believe_is_refused(pot):
    with pytest.raises(LookupError, match="soaked"):
        calibrate(pot, PROBE, "soaked")


def test_a_sensor_that_has_read_nothing_is_refused_without_a_number(pot):
    with pytest.raises(LookupError, match="raw value"):
        calibrate(pot, PROBE, "dry")


def test_run_against_a_stopped_agents_volume_it_finds_the_sensor_by_its_id(pot, tmp_path):
    """What `orexis-calibrate` runs inside the agent's image: the volume, the sensor's id, the label."""
    volume = ox.Store(str(tmp_path / "volume"))
    volume.extend(pot)
    update(volume, f'INSERT DATA {{ GRAPH <{T}binding> {{ <{PROBE}> a sosa:Sensor ; orexis:localId "the_probe" }} }}')
    volume.flush()
    del volume
    assert _main([str(tmp_path / "volume"), "the_probe", "wet", "--raw", "1200"]) == 0
    assert _points(ox.Store(str(tmp_path / "volume")))["wet"] == 1200.0

"""What a sensor's number is, as sensing's rules conclude it: a number no scaling scales is its own
quantity; a two-point scaling the world states rescales it — the pot's probe, its ADC count a moisture
through what it reads dry and wet, unclamped — and a two-point calibration corrects a quantity in its
own unit, after any scaling. The rules run as the deliberator runs them, a revision of the reading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import PUBLIC
from agent.sensing.received import received
from agent.store import document, entry, graphs_of, put_document, rows, update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
RULES = Path(__file__).parents[1] / "rules.ttl"
T = "http://example.org/test#"
PROBE = T + "probe"

#  THE PROBE'S SCALING, as a world states it beside the sensor: 3200 in dry air, 1300 in water.
SCALING = f"""<{T}probe_scaling> a sensing:TwoPointScaling ; sensing:scales <{PROBE}> ;
    sensing:point [ rdfs:label "dry" ; sensing:reads 3200 ; sensing:standsFor 0.0 ] ,
                  [ rdfs:label "wet" ; sensing:reads 1300 ; sensing:standsFor 1.0 ] ."""
#  AND A CORRECTION OF ITS MOISTURE in its own unit: it reads 0.02 at nought and 0.98 at one.
CALIBRATION = f"""<{T}probe_calibration> a sensing:TwoPointCalibration ; sensing:corrects <{PROBE}> ;
    sensing:point [ rdfs:label "low" ; sensing:reads 0.02 ; sensing:standsFor 0.0 ] ,
                  [ rdfs:label "high" ; sensing:reads 0.98 ; sensing:standsFor 1.0 ] ."""


@pytest.fixture
def pot(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(RULES))
    return store


def _stated(store, *said: str) -> None:
    """What the world states beside the sensor, in a public graph of its own."""
    update(store, f"""PREFIX sensing: <http://example.org/orexis/sensing#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{ GRAPH <{T}instruments> {{ {" ".join(said)} }}
  {entry(store, T + "instruments", "http://example.org/orexis#PublicGraph", "http://example.org/orexis#Asserted")} }}""")


def _read(store, snapshots, number) -> dict:
    """A reading of `number`, revised beside public knowledge as belief's part revises it: what the
    rules concluded of it."""
    (graph,) = received(store, snapshots.ME, PROBE, f'{{"value": {number}}}'.encode(), snapshots.NOW)
    revise(store, graph, read=graphs_of(store, PUBLIC))
    found = rows(store, "SELECT ?scaled ?reading WHERE { ?o sensing:scaledResult ?scaled ; sosa:hasSimpleResult ?reading }",
                 [graph, graph + "/revisions"])
    return {k: float(v) for k, v in found[0].items()} if found else {}


def test_a_number_no_scaling_scales_is_its_own_quantity(pot, snapshots):
    assert _read(pot, snapshots, 0.22) == {"scaled": 0.22, "reading": 0.22}


def test_a_count_is_rescaled_on_the_line_through_the_two_points(pot, snapshots):
    """Halfway between dry and wet is half; water past the wet point reads past one, unclamped."""
    _stated(pot, SCALING)
    assert _read(pot, snapshots, 2250) == {"scaled": 0.5, "reading": 0.5}
    assert _read(pot, snapshots, 1110)["reading"] == 1.1


def test_a_calibration_corrects_the_scaled_quantity_in_its_own_unit(pot, snapshots):
    """Scaled half is corrected to half; scaled one, the wet point, is corrected past it."""
    _stated(pot, SCALING, CALIBRATION)
    assert _read(pot, snapshots, 2250) == {"scaled": 0.5, "reading": 0.5}
    assert _read(pot, snapshots, 1300) == {"scaled": 1.0, "reading": round(0.98 / 0.96, 6)}


def test_a_scaling_with_one_point_concludes_no_quantity(pot, snapshots):
    """Two points make a line and one does not: the number stays a number, and no side is said of it."""
    _stated(pot, SCALING.replace(''' ,
                  [ rdfs:label "wet" ; sensing:reads 1300 ; sensing:standsFor 1.0 ]''', ""))
    assert _read(pot, snapshots, 2250) == {}

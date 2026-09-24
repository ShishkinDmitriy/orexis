"""The wiring: my sensors from the world, in sensing's, SOSA's and SSN's words and nobody else's."""

from __future__ import annotations

from agent.sensing.wiring import sensors_of

WORLD = """
@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix sensing: <http://example.org/orexis/sensing#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix ssn: <http://www.w3.org/ns/ssn/> .
@prefix codec: <http://example.org/orexis/codec#> .
@prefix scaling: <http://example.org/orexis/scaling#> .

GRAPH :ontology { }
GRAPH :world {
  :keeper a orexis:Agent ; sensing:polls :probe , :thermometer .
  :board a ssn:System ; ssn:hasSubSystem :probe , :thermometer ; sensing:senseMode sensing:ScheduledProcedure .
  :probe a sosa:Sensor ; sensing:monitors :zz ; sosa:observes :moisture ; sensing:samples :patch ;
         sensing:readingPointer "/soil" ; codec:decodedBy codec:Json ; scaling:scaledBy scaling:Identity ;
         scaling:quantityUnit <http://qudt.org/vocab/unit/UNITLESS> .
  :thermometer a sosa:Sensor ; sensing:monitors :zz ; sosa:observes :warmth .
}
GRAPH :catalogue {
  :catalogue a orexis:CatalogueGraph , orexis:Graph .
  :ontology a orexis:OntologyGraph , orexis:PublicGraph , orexis:Graph .
  :world a orexis:PublicGraph , orexis:Graph .
}
"""
TEST = "http://example.org/test#"


def test_two_sensors_of_one_board_with_the_mode_read_through_ssn(snapshots, tmp_path):
    store = snapshots.stand_in(tmp_path / "wiring.trig", WORLD)
    probe, thermometer = sensors_of(store, TEST + "keeper")
    assert probe.uri == TEST + "probe" and probe.subject == TEST + "zz" and probe.observes == TEST + "moisture"
    assert probe.sample == TEST + "patch" and probe.feature == TEST + "patch"
    assert probe.sense_mode == "http://example.org/orexis/sensing#ScheduledProcedure"
    assert probe.pointer == "/soil" and probe.decoded_by == "http://example.org/orexis/codec#Json"
    assert probe.scaled_by == "http://example.org/orexis/scaling#Identity"
    assert probe.unit == "http://qudt.org/vocab/unit/UNITLESS"
    assert thermometer.observes == TEST + "warmth" and thermometer.feature == TEST + "zz"
    assert thermometer.sense_mode == probe.sense_mode and thermometer.pointer is None


def test_the_store_speaks_no_transport(snapshots, tmp_path):
    store = snapshots.stand_in(tmp_path / "wiring.trig", WORLD)
    assert not any("mqtt" in q.predicate.value for q in store), "the wiring needs no transport word"
    assert sensors_of(store, TEST + "nobody") == ()

"""SHACL shape tests — validate in-memory graphs, no Fuseki needed."""

import rdflib
from pyshacl import validate

from agora.config import PROJECT_ROOT

ONT_DIR = PROJECT_ROOT.parent / "ontology"

GOOD = """
@prefix agora: <http://example.org/agora#> .
@prefix sosa:  <http://www.w3.org/ns/sosa/> .
@prefix prov:  <http://www.w3.org/ns/prov#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .

agora:obs_fern a sosa:Observation ;
  sosa:hasFeatureOfInterest agora:fern ;
  sosa:observedProperty agora:SoilMoisture ;
  sosa:hasSimpleResult "0.18"^^xsd:decimal ;
  sosa:resultTime "2026-08-02T00:00:00+00:00"^^xsd:dateTime ;
  sosa:madeBySensor agora:moisture_sensor_fern ;
  agora:underWorldVersion 1 ;
  prov:wasGeneratedBy agora:fern .

agora:fern a agora:Plant ; agora:servedBy agora:barrel1 ; agora:hasTarget 0.55 .
agora:barrel1 a agora:WaterSource ; agora:suppliedBy agora:supplier .
agora:supplier a agora:Supplier .
"""


def _conforms(ttl: str) -> bool:
    data = rdflib.Graph().parse(data=ttl, format="turtle")
    ont = rdflib.Graph().parse(str(ONT_DIR / "agora.ttl"), format="turtle")
    shapes = rdflib.Graph().parse(str(ONT_DIR / "shapes.ttl"), format="turtle")
    conforms, _, _ = validate(data, shacl_graph=shapes, ont_graph=ont, inference="rdfs")
    return conforms


def test_wellformed_conforms():
    assert _conforms(GOOD)


def test_missing_result_fails():
    assert not _conforms(GOOD.replace('  sosa:hasSimpleResult "0.18"^^xsd:decimal ;\n', ""))


def test_self_asserted_provenance_conforms():
    # Trusted-agent mode: a plant authoring its own reading is valid.
    assert _conforms(GOOD)  # GOOD is prov:wasGeneratedBy agora:fern


def test_missing_provenance_fails():
    bad = GOOD.replace(
        "  agora:underWorldVersion 1 ;\n  prov:wasGeneratedBy agora:fern .",
        "  agora:underWorldVersion 1 .",
    )
    assert not _conforms(bad)


def test_missing_world_version_fails():
    assert not _conforms(GOOD.replace("  agora:underWorldVersion 1 ;\n", ""))


def test_target_out_of_range_fails():
    assert not _conforms(GOOD.replace("agora:hasTarget 0.55", "agora:hasTarget 1.5"))


def test_source_without_supplier_fails():
    assert not _conforms(GOOD.replace("agora:barrel1 a agora:WaterSource ; agora:suppliedBy agora:supplier .", "agora:barrel1 a agora:WaterSource ."))

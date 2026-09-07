"""A reading's identity is its cell (#573): the partition every reader already implies."""
from __future__ import annotations

import rdflib

from orexis_agent_deliberation import partition, signature

SOSA = "http://www.w3.org/ns/sosa/"
PFX = ("@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix sosa: <http://www.w3.org/ns/sosa/> . "
       "@prefix ex: <http://example.org/x#> .\n")


def test_the_thresholds_are_read_off_the_shapes_that_bound_a_reading():
    """The derived region and envelope form: a qualified value shape pinning the property by
    `sh:hasValue` beside a property shape on `sosa:hasSimpleResult` carrying a bound."""
    g = rdflib.Graph()
    g.parse(data=PFX + """
        ex:Region a sh:NodeShape ; sh:property [ sh:path ex:any ; sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ex:Moisture ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:maxExclusive 0.3 ] ] ] ;
          sh:property [ sh:path ex:any ; sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ex:Moisture ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:minExclusive 0.6 ] ] ] .
        ex:Other a sh:NodeShape ; sh:property [ sh:path sosa:hasSimpleResult ; sh:minInclusive 5 ] .
    """, format="turtle")
    found = partition.thresholds_of(g)
    assert found == {"http://example.org/x#Moisture": {0.3, 0.6}}, found
    #  A bound with no pinned property says nothing about any property: it is not read.


def test_a_select_comparing_a_reading_against_a_number_adds_a_threshold_and_against_a_variable_refuses():
    readable = """SELECT ?this WHERE { ?o sosa:observedProperty <http://example.org/x#Moisture> ;
                                          sosa:hasSimpleResult ?v . FILTER(?v < 0.4) }"""
    unreadable = """SELECT ?this WHERE { ?o sosa:observedProperty <http://example.org/x#Level> ;
                                            sosa:hasSimpleResult ?level . FILTER(?level >= ?litres) }"""
    about = """SELECT ?this WHERE { ?o sosa:observedProperty $about ; sosa:hasSimpleResult ?v . FILTER(?v > 0.05) }"""
    found, unreadable_props = partition.readers_of([readable, unreadable, about],
                                                   about="http://example.org/x#Moisture")
    assert found == {"http://example.org/x#Moisture": {0.4, 0.05}}, found
    assert unreadable_props == {"http://example.org/x#Level"}
    cells = partition.cells_of((), [readable, unreadable, about], about="http://example.org/x#Moisture")
    assert cells == {"http://example.org/x#Moisture": (0.05, 0.4)}, "the level stays point-valued"


def test_a_value_falls_in_one_cell_with_its_bounds_and_the_ends_are_open():
    t = (0.1, 0.3, 0.45)
    assert partition.cell_of(0.05, t) == ("cell", None, 0.1)
    assert partition.cell_of(0.1, t) == ("cell", 0.1, 0.3), "the low bound is inclusive"
    assert partition.cell_of(0.25, t) == partition.cell_of(0.27, t) == ("cell", 0.1, 0.3)
    assert partition.cell_of(0.3, t) == ("cell", 0.3, 0.45), "the high bound is exclusive"
    assert partition.cell_of(0.9, t) == ("cell", 0.45, None)
    assert partition.cell_of("dry", t) == ("cell", "dry", "dry"), "a value that is not a number is its own cell"


def test_facts_by_number_restate_by_cell_only_where_the_partition_names_the_property():
    key = ((SOSA + "hasFeatureOfInterest", "urn:pot"), (SOSA + "observedProperty", "http://example.org/x#Moisture"))
    other = ((SOSA + "hasFeatureOfInterest", "urn:butt"), (SOSA + "observedProperty", "http://example.org/x#Level"))
    facts = frozenset({("keyed", SOSA + "Observation", key, SOSA + "hasSimpleResult", 0.27),
                       ("keyed", SOSA + "Observation", other, SOSA + "hasSimpleResult", 3.0),
                       ("urn:s", "urn:p", "urn:o")})
    cells = {"http://example.org/x#Moisture": (0.1, 0.3)}
    out = signature.to_cells(facts, cells)
    assert ("keyed", SOSA + "Observation", key, SOSA + "hasSimpleResult", ("cell", 0.1, 0.3)) in out
    assert ("keyed", SOSA + "Observation", other, SOSA + "hasSimpleResult", 3.0) in out, "the level keeps its number"
    assert ("urn:s", "urn:p", "urn:o") in out and len(out) == 3
    assert signature.to_cells(out, cells) == out, "restating a cell is idempotent"

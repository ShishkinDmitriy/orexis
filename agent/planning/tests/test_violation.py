"""The met-test compiler: a shape, authored positive, compiled into the one select whose rows are
its violations — planning's, since a met-test and the words it reads (`planning:about`)
are the search's."""

from __future__ import annotations

import pyoxigraph as ox
import rdflib

from agent.planning import violation
from agent.store import NAMESPACES

T = "http://example.org/test#"
SHAPE = f"""
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix planning: <http://example.org/orexis/planning#> .
<{T}full> a sh:NodeShape ; sh:targetClass <{T}Tank> ;
    sh:property [ sh:path <{T}level> ; sh:minInclusive 10 ;
                  planning:about <{T}level> ] .
"""


def _world() -> ox.Store:
    st = ox.Store()
    st.load(f"<{T}low> a <{T}Tank> ; <{T}level> 5 . <{T}high> a <{T}Tank> ; <{T}level> 12 .".encode(),
            format=ox.RdfFormat.TURTLE)
    return st


def test_the_unmet_select_answers_the_focus_nodes_that_violate():
    shapes = rdflib.Graph().parse(data=SHAPE, format="turtle")
    rows = list(_world().query(violation.unmet_select(shapes, rdflib.URIRef(T + "full")), prefixes=NAMESPACES))
    assert [r["this"].value for r in rows] == [T + "low"]


def test_the_report_says_what_a_violation_is_about():
    shapes = rdflib.Graph().parse(data=SHAPE, format="turtle")
    (row,) = list(_world().query(violation.report_select(shapes, rdflib.URIRef(T + "full")), prefixes=NAMESPACES))
    assert row["this"].value == T + "low"
    assert row["_about"].value == T + "level"

"""The met-test compiler: a shape, authored positive, compiled into the one select whose rows are
its violations — planning's, since a met-test and the words it reads (`planning:about`)
are the search's."""

from __future__ import annotations

import pyoxigraph as ox
import pytest
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


# --- the avoided state: planning:unmetWhen, unmet where its select yields a row (#892) ----------

AVOIDED = f"""
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix planning: <http://example.org/orexis/planning#> .
<{T}low_tank> planning:about sh:this ;
    sh:select "SELECT $this ?value WHERE {{ $this a <{T}Tank> ; <{T}level> ?value . FILTER(?value < 10) }}" .
"""


def _rows(select: str) -> list[dict]:
    found = _world().query(select, prefixes=NAMESPACES)
    return [{v.value: (s[v].value if s[v] is not None else None) for v in found.variables} for s in found]


def test_the_entered_select_answers_one_row_per_instance_in_the_avoided_state_with_its_offending_value():
    """The report's shape, unnegated: `$this` the instance, `?value` the offending value, the
    one way of failing nought, and what the node says it is about — the instance itself."""
    shapes = rdflib.Graph().parse(data=AVOIDED, format="turtle")
    (row,) = _rows(violation.entered_select(shapes, rdflib.URIRef(T + "low_tank")))
    assert row == {"this": T + "low", "_constraint": "0", "_offending": "5", "_about": T + "low"}


def test_an_avoided_state_narrowed_by_a_target_node_answers_for_that_instance_alone():
    """What the derivation writes when it narrows a want to its instance: the same select with
    `sh:targetNode`, held to the one instance as a shape's target holds its rows."""
    shapes = rdflib.Graph().parse(data=AVOIDED, format="turtle")
    node = rdflib.URIRef(T + "low_tank")
    shapes.add((node, violation.SH.targetNode, rdflib.URIRef(T + "high")))
    assert _rows(violation.entered_select(shapes, node)) == []
    shapes.remove((node, violation.SH.targetNode, None))
    shapes.add((node, violation.SH.targetNode, rdflib.URIRef(T + "low")))
    assert [r["this"] for r in _rows(violation.entered_select(shapes, node))] == [T + "low"]


def test_an_avoided_state_that_is_not_one_select_refuses():
    """A node with no select would read as met for ever; a shape where an avoided state was
    expected is not compiled inside out — both refuse, named, and `weigh` leaves the desire
    unjudged rather than judged quietly."""
    shapes = rdflib.Graph().parse(data=AVOIDED, format="turtle")
    node = rdflib.URIRef(T + "low_tank")
    shapes.add((node, violation.SH.select, rdflib.Literal("SELECT $this WHERE { $this a <urn:x> }")))
    with pytest.raises(violation.Unsupported, match="one sh:select"):
        violation.entered_select(shapes, node)
    shapes.remove((node, violation.SH.select, None))
    with pytest.raises(violation.Unsupported, match="one sh:select"):
        violation.entered_select(shapes, node)
    with pytest.raises(violation.Unsupported, match="not a shape"):
        violation.entered_select(rdflib.Graph().parse(data=SHAPE, format="turtle"), rdflib.URIRef(T + "full"))

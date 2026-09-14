"""The search's verdicts are queries, held to the judge by parity (#548).

The law and the winner's legality used to cross the world into rudof per verdict. Now every
shape the search judges by is compiled to a select whose rows are its violations, run in
the imaginarium at the node's graph, and rudof stays at the gates. What makes that safe is
this file: the compiled rows and the judge's report are held to one answer, feature by
feature on toy worlds and whole on a shipped world — the way the inference closure is held
to pyshacl. A parity that only ever saw agreement about nothing would agree by accident, so
the world case breaks a shape on purpose and pins that both engines refuse it.
"""
from __future__ import annotations

import io
import json

import pyoxigraph as ox
import pytest
import rdflib

from conftest import build_agent, genesis_store
from orexis_agent_deliberation import judge as J
from orexis_agent_deliberation.conformance import _shapes_and_vocabulary, legality_selects
from orexis_agent_deliberation.planner import Planner, _Node
from orexis_agent_progression.ontology import STATE_GRAPH
from orexis_agent_progression.store import NAMESPACES, bindings
from orexis_agent_progression.violation import Unsupported, report_select, report_selects

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
PFX = ("@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix ex: <http://example.org/x#> . "
       "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
S = "ex:S a sh:NodeShape ; sh:targetClass ex:T ; "

#  One case per feature the packages' shapes use beyond the want fragment: (shape, data).
CASES = {
    "minCount 2": (S + "sh:property [ sh:path ex:p ; sh:minCount 2 ] .",
                   "ex:a a ex:T ; ex:p 1 . ex:b a ex:T ; ex:p 1, 2 . ex:c a ex:T ."),
    "maxCount 1": (S + "sh:property [ sh:path ex:p ; sh:maxCount 1 ] .",
                   "ex:a a ex:T ; ex:p 1 . ex:b a ex:T ; ex:p 1, 2 . ex:c a ex:T ."),
    "datatype": (S + "sh:property [ sh:path ex:p ; sh:datatype xsd:integer ] .",
                 "ex:a a ex:T ; ex:p 1 . ex:b a ex:T ; ex:p 1.5 . ex:c a ex:T ; ex:p 'x' . "
                 "ex:d a ex:T ; ex:p ex:z ."),
    "nodeKind IRI, a blank counts as one at the border": (
        S + "sh:property [ sh:path ex:p ; sh:nodeKind sh:IRI ] .",
        "ex:a a ex:T ; ex:p ex:z . ex:b a ex:T ; ex:p 'x' . ex:c a ex:T ; ex:p [] ."),
    "in": (S + "sh:property [ sh:path ex:p ; sh:in ( ex:u ex:v ) ] .",
           "ex:a a ex:T ; ex:p ex:u . ex:b a ex:T ; ex:p ex:w . ex:c a ex:T ; ex:p 3 ."),
    "or of property shapes": (
        S + "sh:or ( [ sh:path ex:p ; sh:minCount 1 ] [ sh:path ex:q ; sh:minCount 1 ] ) .",
        "ex:a a ex:T ; ex:p 1 . ex:b a ex:T ; ex:q 1 . ex:c a ex:T . ex:d a ex:T ; ex:p 1 ; ex:q 1 ."),
    "xone": (S + "sh:xone ( [ sh:property [ sh:path ex:p ; sh:minCount 1 ] ] "
                 "[ sh:property [ sh:path ex:q ; sh:minCount 1 ] ] ) .",
             "ex:a a ex:T ; ex:p 1 . ex:b a ex:T ; ex:q 1 . ex:c a ex:T . ex:d a ex:T ; ex:p 1 ; ex:q 1 ."),
    "node": (S + "sh:property [ sh:path ex:p ; sh:node [ a sh:NodeShape ; sh:property "
                 "[ sh:path ex:r ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ] ] .",
             "ex:a a ex:T ; ex:p ex:x . ex:x ex:r ex:y . ex:b a ex:T ; ex:p ex:w . "
             "ex:c a ex:T ; ex:p ex:m . ex:m ex:r 'lit' ."),
    "lessThanOrEquals": (S + "sh:property [ sh:path ex:lo ; sh:lessThanOrEquals ex:hi ] .",
                         "ex:a a ex:T ; ex:lo 1 ; ex:hi 2 . ex:b a ex:T ; ex:lo 3 ; ex:hi 2 . "
                         "ex:c a ex:T ; ex:lo 2 ; ex:hi 2 ."),
    "a SPARQL target": (
        "ex:S a sh:NodeShape ; sh:target [ a sh:SPARQLTarget ; sh:select "
        "'SELECT ?this WHERE { ?this <http://example.org/x#k> ?any }' ] ; "
        "sh:property [ sh:path ex:p ; sh:minCount 1 ] .",
        "ex:a ex:k 1 ; ex:p 1 . ex:b ex:k 1 . ex:c a ex:T ."),
    "a property's own warning is not a violation": (
        S + "sh:property [ sh:path ex:p ; sh:minCount 1 ; sh:severity sh:Warning ] ; "
            "sh:property [ sh:path ex:q ; sh:minCount 1 ] .",
        "ex:a a ex:T ; ex:p 1 . ex:b a ex:T ; ex:q 1 . ex:c a ex:T ."),
    "the node's warning does not reach its property": (
        S + "sh:severity sh:Warning ; sh:property [ sh:path ex:p ; sh:minCount 1 ] .",
        "ex:a a ex:T ; ex:p 1 . ex:c a ex:T ."),
    "the node's warning covers its sparql constraint": (
        S + "sh:severity sh:Warning ; sh:sparql [ sh:select "
            "'SELECT $this WHERE { $this <http://example.org/x#p> ?v }' ] .",
        "ex:a a ex:T ; ex:p 1 . ex:c a ex:T ."),
    "a sparql constraint's own severity is ignored": (
        S + "sh:sparql [ sh:severity sh:Warning ; sh:select "
            "'SELECT $this WHERE { $this <http://example.org/x#p> ?v }' ] .",
        "ex:a a ex:T ; ex:p 1 . ex:c a ex:T ."),
    "qualifiedMinCount 2 over a node-level class": (
        S + "sh:property [ sh:path ex:p ; sh:qualifiedValueShape [ sh:class ex:C ] ; "
            "sh:qualifiedMinCount 2 ] .",
        "ex:a a ex:T ; ex:p ex:x, ex:y . ex:x a ex:C . ex:y a ex:C . "
        "ex:b a ex:T ; ex:p ex:x, ex:z . ex:c a ex:T ."),
    "hasValue and class": (
        S + "sh:property [ sh:path ex:p ; sh:hasValue ex:u ] ; "
            "sh:property [ sh:path ex:q ; sh:class ex:C ] .",
        "ex:a a ex:T ; ex:p ex:u ; ex:q ex:k . ex:k a ex:C . ex:b a ex:T ; ex:p ex:v ; ex:q ex:k . "
        "ex:c a ex:T ; ex:p ex:u ; ex:q ex:n ."),
}


def _rows(select: str, data_ttl: str) -> set[str]:
    st = ox.Store()
    st.load(data_ttl.encode(), format=ox.RdfFormat.TURTLE)
    out = io.BytesIO()
    st.query(select, prefixes=NAMESPACES).serialize(output=out, format=ox.QueryResultsFormat.JSON)
    return {r["this"]["value"] for r in json.loads(out.getvalue())["results"]["bindings"]}


@pytest.mark.parametrize("case", list(CASES))
def test_a_compiled_report_agrees_with_the_judge_feature_by_feature(case):
    shape_ttl, data_ttl = CASES[case]
    shapes = rdflib.Graph()
    shapes.parse(data=PFX + shape_ttl, format="turtle")
    data = rdflib.Graph()
    data.parse(data=PFX + data_ttl, format="turtle")
    select = report_select(shapes, rdflib.URIRef("http://example.org/x#S"))
    compiled = _rows(select, PFX + data_ttl) if select else set()
    judged = {v.focus for v in J.verdicts(J.crossed_text(data.serialize(format="nt")), shapes)[0]
              if v.severity == J.VIOLATION}
    assert compiled == judged, f"{case}: compiled {compiled} against the judge's {judged}"


def test_both_answers_are_reached_so_the_feature_parity_is_not_vacuous():
    """Every case above must find some focus violating and some conforming, or a compiler
    that answered nothing would agree with a judge that answered nothing."""
    empty, full = [], []
    for case, (shape_ttl, data_ttl) in CASES.items():
        shapes = rdflib.Graph()
        shapes.parse(data=PFX + shape_ttl, format="turtle")
        select = report_select(shapes, rdflib.URIRef("http://example.org/x#S"))
        found = _rows(select, PFX + data_ttl) if select else set()
        (empty if not found else full).append(case)
    assert full, "no case violates anything"
    assert set(empty) <= {"the node's warning covers its sparql constraint"}, \
        f"cases that violate nothing: {empty}"


# --- a shipped world, whole ------------------------------------------------------------------

def _carriers(*graphs) -> dict:
    """rudof's `sh:sourceShape` (a named or skolemized property/sparql carrier) → its node shape."""
    out = {}
    for shapes in graphs:
        for s in shapes.subjects(rdflib.RDF.type, SH.NodeShape):
            name = J._SKOLEM + str(s) if isinstance(s, rdflib.BNode) else str(s)
            out[name] = str(s)
            for link in (SH.property, SH.sparql):
                for c in shapes.objects(s, link):
                    out[J._SKOLEM + str(c) if isinstance(c, rdflib.BNode) else str(c)] = str(s)
    return out


def _both(planner, agent, graph) -> tuple[set, set]:
    """(compiled, judged): the (shape, focus) pairs each engine refuses at `graph`."""
    node = _Node(graph=graph)
    compiled = {(shape, focus) for shape, focus, _, _ in planner._illegal(node, planner._compiled.legal)}
    _, shapes = _shapes_and_vocabulary()
    package, own = J.verdicts(planner._border(node), shapes, planner._compiled.held)
    to_shape = _carriers(shapes, planner._compiled.held)
    judged = ({(to_shape.get(v.source, v.source), v.focus) for v in package
               if v.severity == J.VIOLATION and v.focus == agent.me.uri}
              | {(to_shape.get(v.source, v.source), v.focus) for v in own
                 if v.severity == J.VIOLATION})
    return compiled, judged


def test_the_legality_check_agrees_with_the_judge_on_a_shipped_world_and_a_broken_one(monkeypatch):
    agent = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    planner = Planner(agent, agent.me)
    desire = next(d for d in agent.pursuing() if getattr(d, "observed_property", None))
    here = planner._begin(desire)
    try:
        assert planner._compiled.legal, "nothing compiled — the check would accept every world"
        root_compiled, root_judged = _both(planner, agent, here.graph)
        assert root_compiled == root_judged
        #  A child that breaks a package shape about this agent: a subscribing interval
        #  below the constitutional floor. Both engines must refuse it, by the same shape.
        row = type("R", (), {"action": "urn:x:break", "via": "urn:x:v", "about": None})()
        xsd_int = ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer")
        broken = planner.imaginarium.reached(STATE_GRAPH, (row,), [ox.Triple(
            ox.NamedNode(agent.me.uri),
            ox.NamedNode("http://example.org/orexis/sensing#fastSleepS"),
            ox.Literal("5", datatype=xsd_int))], [])
        compiled, judged = _both(planner, agent, broken)
        assert compiled == judged
        assert compiled and compiled != root_compiled, \
            "the broken world must be refused where the root is not, or the parity proved nothing"
    finally:
        planner.imaginarium = None


def test_a_held_shape_the_compiler_cannot_say_refuses_the_pass(monkeypatch):
    """Never a legality check that quietly judges less than the gates: a held shape outside
    the fragment raises at `_begin`, named."""
    from orexis_agent_deliberation import planner as search
    agent = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    odd = rdflib.Graph()
    odd.parse(data=PFX + f"ex:Odd a sh:NodeShape ; sh:targetNode <{agent.me.uri}> ; "
                         "sh:property [ sh:path ex:p ; sh:pattern '^x' ] .", format="turtle")
    monkeypatch.setattr(search, "held_shapes", lambda data, me: odd)
    planner = Planner(agent, agent.me)
    desire = next(d for d in agent.pursuing() if getattr(d, "observed_property", None))
    with pytest.raises(Unsupported, match="pattern"):
        planner._begin(desire)
    planner.imaginarium = None


def test_the_packages_shapes_all_compile_about_an_agent():
    """Every targeted shape the packages ship states something the compiler can say, so the
    legality check covers what the gates cover — a refusal here names the shape to widen
    the compiler for, before any pass meets it."""
    selects = legality_selects("http://example.org/orexis/world/simulation#fern_agent")
    _, shapes = _shapes_and_vocabulary()
    targeted = {s for s in shapes.subjects(rdflib.RDF.type, SH.NodeShape)
                if any((s, t, None) in shapes for t in (SH.targetNode, SH.targetClass, SH.targetSubjectsOf,
                                                         SH.targetObjectsOf, SH.target))}
    assert len(selects) >= 60 and set(selects) <= targeted
    assert report_selects(shapes, focus_node=None), "unfocused, the same shapes compile"

"""The judge's door for a world already at the border as text (#485)."""
from __future__ import annotations

import rdflib

from orexis_agent_deliberation.judge import _SKOLEM, crossed_text, judge

_SH = "http://www.w3.org/ns/shacl#"


def test_a_text_border_is_skolemized_by_label_and_literals_are_left_alone():
    nt = ('_:b1 <urn:p> _:b2 .\n'
          '_:b2 <urn:q> "a _:b3 inside a literal" .\n'
          '<urn:s> <urn:r> "plain" .\n')
    out = crossed_text(nt)
    assert f"<{_SKOLEM}b1> <urn:p> <{_SKOLEM}b2> ." in out
    assert f'<{_SKOLEM}b2> <urn:q> "a _:b3 inside a literal" .' in out, \
        "a blank-looking token inside a literal is text, not a node"
    assert "_:b1" not in out and "_:b2" not in out
    assert crossed_text(out) == out, "naming is idempotent — a crossed border crosses again unchanged"


def test_a_blank_focus_node_is_judged_on_the_text_path():
    """The reason the border is skolemized at all: rudof pre-binds a sh:sparql constraint's
    $this through VALUES, where a blank node is illegal. A shape over a blank instance must
    still find its violation when the world arrives as the store's own dump."""
    data = crossed_text('_:e <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <urn:Envelope> .\n'
                        '_:e <urn:weight> "12"^^<http://www.w3.org/2001/XMLSchema#integer> .\n')
    shapes = rdflib.Graph()
    shapes.parse(data=f"""
        @prefix sh: <{_SH}> .
        <urn:Heavy> a sh:NodeShape ; sh:targetClass <urn:Envelope> ; sh:severity sh:Violation ;
            sh:sparql [ sh:select "SELECT $this WHERE {{ $this <urn:weight> ?w . FILTER(?w > 10) }}" ] .
    """, format="turtle")
    results, report = judge(data, shapes)
    focus = {str(o) for o in results.objects(None, rdflib.URIRef(_SH + "focusNode"))}
    assert focus == {_SKOLEM + "e"}, report


def _border_and_planner(monkeypatch):
    """A real world at the border, and the planner that holds it in the imaginarium."""
    import sys
    sys.path.insert(0, "tests")
    from conftest import build_agent, genesis_store
    from orexis_agent_deliberation.planner import Planner
    agent = build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)
    planner = Planner(agent, agent.me)
    desire = next(d for d in agent.pursuing() if getattr(d, "observed_property", None))
    here = planner._begin(desire)
    return agent, planner, here, planner._border(here)


def test_verdicts_agree_with_the_full_report_and_read_the_data_once(monkeypatch):
    """The parity oracle and the gates' door are one judge: the same world held to the same
    shapes answers the same (severity, focus, source) triples, whether the report is read
    as N-Triples by the store's parser or as Turtle by rdflib — and the world crosses into
    rudof once for however many shapes graphs are asked."""
    from orexis_agent_deliberation import judge as J
    from orexis_agent_deliberation.conformance import _shapes_and_vocabulary
    agent, planner, here, border = _border_and_planner(monkeypatch)
    try:
        _, shapes = _shapes_and_vocabulary()
        held = planner._held
        reads = []
        real = J.Rudof.read_data
        monkeypatch.setattr(J.Rudof, "read_data", lambda self, *a, **k: reads.append(1) or real(self, *a, **k))
        package, own = J.verdicts(border, shapes, held)
        assert reads == [1], "two shapes graphs, one reading of the data"
        for graph, found in ((shapes, package), (held, own)):
            results, _ = J.judge(border, graph)
            expected = {(str(results.value(r, J._SH.resultSeverity)), str(results.value(r, J._SH.focusNode)),
                         str(results.value(r, J._SH.sourceShape)))
                        for r in results.subjects(rdflib.RDF.type, J._SH.ValidationResult)}
            assert {(v.severity, v.focus, v.source) for v in found} == expected
        assert package, "the packages' shapes report something about a fresh world, or this test proves nothing"
    finally:
        planner.imaginarium = None


def test_an_empty_shapes_graph_answers_no_verdicts():
    from orexis_agent_deliberation.judge import verdicts
    assert verdicts('<urn:a> <urn:p> "x" .\n', rdflib.Graph()) == [frozenset()]

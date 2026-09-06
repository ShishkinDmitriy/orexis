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

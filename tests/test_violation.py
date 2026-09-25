"""A want's shape, compiled to the select whose rows violate it — held to the judge by parity.

Two engines read one declaration: the judge (rudof) validates the shape, the store's own engine
runs the compiled select, and the search trusts the second because it costs a millisecond where
the judge's reader floors at tens. That trust is exactly the disagreement this repository closed
once already between pyshacl and the runtime (one-graph-both-engines-read), so every shipped
want is held here to the judge on the same world, met and unmet alike — and a shape the
compiler cannot say REFUSES rather than compiling to something quiet (#497).
"""

import pytest
import rdflib

from conftest import genesis_store

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
STATE_GRAPH = "http://example.org/orexis/graph/sensed"


def _agent(monkeypatch, world, name, pose=None, readings=None):
    from agent_old import genesis, runtime

    monkeypatch.setenv("INFLUX_BUCKET", f"test-{world}")
    monkeypatch.setenv("INFLUX_TOKEN", f"test-token-{world}")
    st = genesis_store(readings, world=world) if readings else genesis_store(world=world)
    if pose:
        st.update("INSERT DATA { GRAPH <%s> { %s } }" % (STATE_GRAPH, pose))
    genesis.classify_kernel_graphs(st, world)
    return runtime.Agent(name, st=st)


def _both_verdicts(agent):
    """For every shape-authored want the agent pursues: (want, compiled says unmet, judge says
    unmet). Wants that are not shapes — patterns, obligations, calls — are not this file's."""
    from orexis_agent_deliberation.conformance import judge
    from orexis_agent_deliberation.planner import Planner
    from orexis_agent_progression.store import bindings

    out = []
    for desire in agent.considering():
        p = Planner(agent, agent.me)
        node = p._begin(desire)
        shape = p._shape_of(desire)
        if shape is None:
            continue
        compiled = bool(bindings(agent.beliefs.query_over(
            p._compiled.unmet, *p._compiled.invariant_graphs, STATE_GRAPH)))
        results, _ = judge(p._border(node), shape)
        judged = bool(list(results.subjects(rdflib.RDF.type, SH.ValidationResult)))
        out.append((desire.uri.rsplit("#", 1)[-1], compiled, judged, desire.state))
    return out


CASES = {
    "fern, dry": ("simulation", "fern", None, {"fern": 0.10}),
    "fern, watered": ("simulation", "fern", None, {"fern": 0.40}),
    "loner's gardener": ("loner", "gardener", None, None),
}


@pytest.mark.parametrize("case", list(CASES))
def test_the_compiled_select_agrees_with_the_judge(monkeypatch, case):
    world, name, pose, readings = CASES[case]
    agent = _agent(monkeypatch, world, name, pose, readings)
    verdicts = _both_verdicts(agent)
    assert verdicts, f"{case}: no shape-authored want to compare — the case asserts nothing"
    for want, compiled, judged, state in verdicts:
        assert compiled == judged, \
            f"{case}, {want}: compiled says {'unmet' if compiled else 'met'}, " \
            f"the judge says {'unmet' if judged else 'met'}"
        #  A sensing want speaks its own vocabulary — `stale`, `unmeasured` — beside met and
        #  unmet; whatever the word, a want the module calls anything but met is one the
        #  compiled select must find violated, and a met one it must find clean.
        assert (state != "met") == compiled, \
            f"{case}, {want}: considering() reports {state} against the compiled {compiled}"


def test_both_answers_are_reached_so_the_parity_is_not_vacuous(monkeypatch):
    """A parity that only ever saw one answer would agree by accident. Delivered and astray,
    home and astray, watered and dry are all above; this pins that both verdicts occur."""
    seen = set()
    for case in ("fern, watered", "fern, dry"):
        world, name, pose, readings = CASES[case]
        for _, compiled, _, _ in _both_verdicts(_agent(monkeypatch, world, name, pose, readings)):
            seen.add(compiled)
    assert seen == {True, False}


def test_a_shape_the_compiler_cannot_say_refuses():
    """A component outside the fragment — `sh:closed` here — raises, named. Never an empty
    pattern, which would read as met for ever: the quiet direction to be wrong."""
    from orexis_agent_progression.violation import Unsupported, unmet_select

    g = rdflib.Graph()
    g.parse(data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/x#> .
        ex:S a sh:NodeShape ; sh:targetClass ex:Thing ; sh:closed true ;
            sh:property [ sh:path ex:p ; sh:hasValue ex:v ] .
        ex:T a sh:NodeShape ; sh:targetClass ex:Thing ;
            sh:property [ sh:path ex:p ; sh:pattern "^x" ] .
        ex:U a sh:NodeShape ; sh:property [ sh:path ex:p ; sh:hasValue ex:v ] .
    """, format="turtle")
    ex = rdflib.Namespace("http://example.org/x#")
    with pytest.raises(Unsupported, match="closed"):
        unmet_select(g, ex.S)
    with pytest.raises(Unsupported, match="pattern"):
        unmet_select(g, ex.T)
    with pytest.raises(Unsupported, match="targets nothing"):
        unmet_select(g, ex.U)


def test_a_select_brings_its_own_prefix_and_the_compiled_query_keeps_it():
    """SPARQL declares a prefix with `PREFIX`, and a `sh:select` is a query like any other.

    Only the BODY of a select is inlined into the compiled branch, so a `PREFIX` line would
    otherwise be dropped and its names left unresolvable — which is why a shape speaking a
    vocabulary the store never loaded had to spell every IRI in full. What the select declared
    is written at the head of the compiled query instead, and the query RUNS, which is what
    this asserts rather than the text it produced.

    Almost every shape needs none: a package's namespace is one the store discovered from that
    package's own ontology, and no shape shipped here declares a prefix of its own.
    """
    import pyoxigraph as ox

    from orexis_agent_progression.store import NAMESPACES
    from orexis_agent_progression.violation import report_select

    g = rdflib.Graph()
    g.parse(data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix orexis: <http://example.org/orexis#> .
        @prefix ex: <http://example.org/nobody-loaded-this#> .
        ex:S a sh:NodeShape ; sh:targetClass ex:Thing ;
            sh:sparql [ sh:prefixes orexis: ; orexis:about sh:this ;
                sh:select '''PREFIX ex: <http://example.org/nobody-loaded-this#>
                    SELECT $this WHERE { $this ex:reads ?v FILTER(?v > 10) }''' ] .
    """, format="turtle")
    select = report_select(g, rdflib.URIRef("http://example.org/nobody-loaded-this#S"))
    assert select.startswith("PREFIX ex: <http://example.org/nobody-loaded-this#>"), select

    store = ox.Store()
    store.update("""INSERT DATA { GRAPH <http://g> {
        <http://example.org/nobody-loaded-this#a> a <http://example.org/nobody-loaded-this#Thing> ;
            <http://example.org/nobody-loaded-this#reads> 40 .
        <http://example.org/nobody-loaded-this#b> a <http://example.org/nobody-loaded-this#Thing> ;
            <http://example.org/nobody-loaded-this#reads> 4 . } }""")
    rows = [str(r["this"].value) for r in store.query(
        select, prefixes=NAMESPACES, default_graph=[ox.NamedNode("http://g")])]
    assert rows == ["http://example.org/nobody-loaded-this#a"], rows


def test_a_select_may_not_redeclare_a_name_that_already_means_something():
    """Two spellings of one name is the confusion prefixes exist to prevent, and the engine
    would take whichever came last. Refused, named, whether the other spelling is the store's
    or another select's in the same shape."""
    from orexis_agent_progression.violation import Unsupported, report_select

    g = rdflib.Graph()
    g.parse(data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix orexis: <http://example.org/orexis#> .
        @prefix ex: <http://example.org/x#> .
        ex:S a sh:NodeShape ; sh:targetClass ex:Thing ;
            sh:sparql [ sh:prefixes orexis: ;
                sh:select '''PREFIX orexis: <http://example.org/somewhere-else#>
                    SELECT $this WHERE { $this orexis:p ?v }''' ] .
        ex:T a sh:NodeShape ; sh:targetClass ex:Thing ;
            sh:sparql [ sh:prefixes orexis: ;
                sh:select '''PREFIX qq: <http://example.org/one#>
                    SELECT $this WHERE { $this qq:p ?v }''' ] ,
                      [ sh:prefixes orexis: ;
                sh:select '''PREFIX qq: <http://example.org/two#>
                    SELECT $this WHERE { $this qq:q ?v }''' ] .
    """, format="turtle")
    ex = rdflib.Namespace("http://example.org/x#")
    with pytest.raises(Unsupported, match="the store calls that prefix"):
        report_select(g, ex.S)
    with pytest.raises(Unsupported, match="declare qq: differently"):
        report_select(g, ex.T)


def test_the_fragment_compiles_to_readable_sparql():
    """The shapes the derivations emit, in one small shape: a sequence path with an inverse
    step, a qualified value shape with min count one, another with max count zero and a
    bound inside, a hasValue, an equals. Each becomes the pattern the SHACL specification
    defines as its violation, and each branch repeats the target so its filters see ?this."""
    from orexis_agent_progression.violation import unmet_select

    g = rdflib.Graph()
    g.parse(data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <http://example.org/x#> .
        ex:S a sh:NodeShape ; sh:targetNode ex:me ;
            sh:property [ sh:path ( ex:for [ sh:inversePath ex:of ] ) ;
                          sh:qualifiedMinCount 1 ;
                          sh:qualifiedValueShape [ sh:property [ sh:path ex:prop ; sh:hasValue ex:m ] ] ] ;
            sh:property [ sh:path ( ex:for [ sh:inversePath ex:of ] ) ;
                          sh:qualifiedMaxCount 0 ;
                          sh:qualifiedValueShape [ sh:property [ sh:path ex:prop ; sh:hasValue ex:m ] ;
                                                   sh:property [ sh:path ex:value ; sh:maxExclusive 0.3 ] ] ] ;
            sh:property [ sh:path ex:at ; sh:equals ex:home ] .
    """, format="turtle")
    text = unmet_select(g, rdflib.URIRef("http://example.org/x#S"))
    assert text.startswith("SELECT DISTINCT ?this WHERE {")
    assert text.count("VALUES ?this { <http://example.org/x#me> }") == 4, \
        "the target is repeated in every branch: one for the min, one for the max, two for equals"
    assert "(<http://example.org/x#for>/^(<http://example.org/x#of>))" in text
    assert "FILTER NOT EXISTS { ?this (<http://example.org/x#for>/^(<http://example.org/x#of>)) ?v" in text
    assert "FILTER(!(" in text and "< \"0.3\"^^<http://www.w3.org/2001/XMLSchema#decimal>" in text

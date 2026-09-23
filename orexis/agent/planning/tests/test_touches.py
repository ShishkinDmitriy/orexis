"""What a text touches — tested where the functions live, over texts small enough to read.

Two kinds of function: over a TEXT or a parsed shape (`parseable`, `reads_of_select`,
`writes_of_construct`, `reads_of_shape`), which own nothing; and over the STORE
(`actions_of`, `stored_edges`), which answer for every action and derivation in it.
"""

from __future__ import annotations

from pathlib import Path

import rdflib
from rdflib import RDF, URIRef
from rdflib.namespace import SH

from orexis.agent import clock
from orexis.agent.store import graphs_of, update
from orexis.agent.planning import touches
from orexis.agent.planning.ontology import DERIVATION_GRAPH

P, Q = URIRef("urn:test:p"), URIRef("urn:test:q")


def test_what_a_select_reads_is_the_predicates_of_its_patterns():
    assert touches.reads_of_select("SELECT ?x WHERE { ?x <urn:test:p> ?y . ?y a <urn:test:C> }") \
        == frozenset({P, RDF.type})


def test_a_pattern_under_not_exists_is_read_too():
    """rdflib leaves it untranslated inside the filter, and a want saying 'unmet while this
    fact is absent' reads that fact's predicate (#523)."""
    assert touches.reads_of_select(
        "SELECT ?x WHERE { ?x a <urn:test:C> FILTER NOT EXISTS { ?x <urn:test:q> ?z } }") \
        == frozenset({Q, RDF.type})


def test_what_a_construct_writes_is_its_template_predicates_and_a_variable_one_is_anything():
    assert touches.writes_of_construct("CONSTRUCT { ?x <urn:test:q> ?v } WHERE { ?x <urn:test:p> ?v }") \
        == frozenset({Q})
    assert touches.writes_of_construct("CONSTRUCT { ?x ?p ?v } WHERE { ?x ?p ?v }") is touches.ANYTHING
    assert touches.writes_of_construct("this is not a query") is touches.ANYTHING, "unreadable is unfiltered"


def test_a_rule_text_is_made_parseable_and_nothing_more():
    assert "?me" in touches.parseable("SELECT ?x WHERE { $me <urn:test:p> ?x }")
    assert "$into(" not in touches.parseable("INSERT { GRAPH $into(x:G) { ?s ?p ?o } } WHERE { ?s ?p ?o }")


def test_what_a_shape_reads_is_its_paths_and_its_target():
    g = rdflib.Graph()
    shape, prop = URIRef("urn:test:shape"), rdflib.BNode()
    g.add((shape, RDF.type, SH.NodeShape)); g.add((shape, SH.targetClass, URIRef("urn:test:C")))
    g.add((shape, SH.property, prop)); g.add((prop, SH.path, P)); g.add((prop, SH.minInclusive, rdflib.Literal(10)))
    assert touches.reads_of_shape(g, shape) == frozenset({P, RDF.type})


def test_actions_of_reads_every_action_the_store_holds(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(Path(__file__).parent / "plans" / "a_low_tank_is_filled.trig")
    (action,) = touches.actions_of(store).items()
    iri, (reads, writes) = action
    assert iri.endswith("#fill")
    assert URIRef("http://example.org/test#level") in reads and URIRef("http://example.org/test#level") in writes


def test_stored_edges_read_the_derivations_genesis_wrote(wants):
    update(wants.store, """INSERT DATA {
  GRAPH <urn:test:derivations> {
    <urn:test:d1> a planning:Derivation ; planning:reads <urn:test:p> ; planning:writes <urn:test:q> .
    <urn:test:d2> a planning:Derivation ; planning:reads planning:Anything }
  GRAPH <urn:test:catalogue> { <urn:test:derivations> a planning:DerivationGraph } }""")
    edges = touches.stored_edges(wants.store, graphs_of(wants.store, DERIVATION_GRAPH))
    assert edges == ((frozenset({P}), frozenset({Q})), (touches.ANYTHING, frozenset()))

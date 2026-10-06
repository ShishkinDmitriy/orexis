"""What a text reads and writes, its footprint — tested where the functions live, over texts small enough to read.

Two kinds of function: over a TEXT or a parsed shape (`parseable`, `reads_of_select`,
`writes_of_construct`, `reads_of_shape`), which own nothing; and over the STORE
(`actions_of`, `stored_edges`), which answer for every action and derivation in it.
"""

from __future__ import annotations

from pathlib import Path

import rdflib
from rdflib import RDF, URIRef
from rdflib.namespace import SH

from agent import clock
from agent.store import graphs_of, update
from agent.planning import footprint
from agent.planning.ontology import DERIVATION_GRAPH

P, Q = URIRef("urn:test:p"), URIRef("urn:test:q")


def test_what_a_select_reads_is_the_predicates_of_its_patterns():
    """A type pattern reads its CLASS: two domains' `a hanoi:Peg` and `a courier:Van` keyed by
    `rdf:type` alone joined every action of both into one scope. A class that is a variable
    reads every type."""
    assert footprint.reads_of_select("SELECT ?x WHERE { ?x <urn:test:p> ?y . ?y a <urn:test:C> }") \
        == frozenset({P, URIRef("urn:test:C")})
    assert footprint.reads_of_select("SELECT ?x WHERE { ?x a ?c }") == frozenset({RDF.type})


def test_a_pattern_under_not_exists_is_read_too():
    """rdflib leaves it untranslated inside the filter, and a want saying 'unmet while this
    fact is absent' reads that fact's predicate (#523)."""
    assert footprint.reads_of_select(
        "SELECT ?x WHERE { ?x a <urn:test:C> FILTER NOT EXISTS { ?x <urn:test:q> ?z } }") \
        == frozenset({Q, URIRef("urn:test:C")})


#  THE ISSUE'S TWO TEXTS, as it states them (#908), with its namespace made an IRI the store
#  need not know; the predicates each must answer are the issue's too.
_A_LIST_UNDER_A_FILTER = ("SELECT ?v WHERE { ?me <urn:m:bidsIn> ?v . "
                          "FILTER NOT EXISTS { ?c <urn:m:calledBy> ?me ; <urn:m:calledOn> ?v } }")
_A_FILTER_IN_A_FILTER = ("SELECT ?v WHERE { ?me <urn:m:bidsIn> ?v . "
                         "FILTER NOT EXISTS { ?c <urn:m:calledOn> ?v . FILTER NOT EXISTS { ?c <urn:m:answered> true } } }")
M = rdflib.Namespace("urn:m:")


def test_a_predicate_list_under_not_exists_reads_every_predicate_of_the_list():
    """`?c :calledBy ?me ; :calledOn ?v` is ONE entry of the parse-tree block, six terms laid flat,
    and read as a triple it was unreadable: the whole text answered anything (#908). An object list
    and a blank node are laid flat the same way."""
    assert footprint.reads_of_select(_A_LIST_UNDER_A_FILTER) == frozenset({M.bidsIn, M.calledBy, M.calledOn})
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { FILTER NOT EXISTS { ?c <urn:m:calledOn> ?v , ?w } }") == frozenset({M.calledOn})
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { FILTER NOT EXISTS { ?c <urn:m:p> [ <urn:m:q> ?v ] } }") == frozenset({M.p, M.q})
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { FILTER NOT EXISTS { ?c a <urn:m:C> ; <urn:m:p> ?v } }") == frozenset({M.C, M.p}), \
        "a type pattern in the list reads its class, as one in the group does"
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { FILTER NOT EXISTS { ?c ?p ?v ; <urn:m:r> ?w } }") is footprint.ANYTHING, \
        "a variable predicate in the list is still anything"


def test_a_not_exists_nested_in_a_not_exists_is_read_too():
    """rdflib pops a filter out of the parse-tree group it was found in and keeps the translated
    group beside it, as an attribute; read off the parse tree alone the inner filter was missing
    and the answer under-read, the unsafe side: two presents differing only in `answered` hashed
    as one (#908). Three deep, inside an OPTIONAL, under a `BIND(EXISTS …)`, the same."""
    assert footprint.reads_of_select(_A_FILTER_IN_A_FILTER) == frozenset({M.bidsIn, M.calledOn, M.answered})
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { ?me <urn:m:a> ?v FILTER NOT EXISTS { ?c <urn:m:b> ?v "
        "FILTER NOT EXISTS { ?c <urn:m:c> ?v FILTER NOT EXISTS { ?c <urn:m:d> ?v } } } }") \
        == frozenset({M.a, M.b, M.c, M.d})
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { ?c <urn:m:p> ?v OPTIONAL { ?c <urn:m:q> ?w FILTER NOT EXISTS { ?w <urn:m:r> ?x ; <urn:m:s> ?y } } }") \
        == frozenset({M.p, M.q, M.r, M.s})
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { ?c <urn:m:p> ?v . FILTER NOT EXISTS { ?c <urn:m:q> ?v . OPTIONAL { ?c <urn:m:o> ?w } "
        "MINUS { ?c <urn:m:m> ?z } FILTER EXISTS { ?c <urn:m:e> ?y } } }") == frozenset({M.p, M.q, M.o, M.m, M.e}), \
        "an OPTIONAL, a MINUS and an EXISTS inside the block are read as the block is"
    assert footprint.reads_of_select(
        "SELECT ?v WHERE { ?c <urn:m:p> ?v BIND(EXISTS { ?c <urn:m:q> ?w ; <urn:m:r> ?x } AS ?b) }") \
        == frozenset({M.p, M.q, M.r})


def test_the_patterns_of_a_precondition_are_the_same_triples_the_predicates_were_read_off():
    """One walk serves the read set and the fillings: `_patterns`, which `atoms_of` keys a filling
    by, answers every pattern of both shapes, each once, where it answered anything for the first
    and left the inner pattern out of the second."""
    c, me, v = rdflib.Variable("c"), rdflib.Variable("me"), rdflib.Variable("v")
    assert footprint._patterns(_A_LIST_UNDER_A_FILTER) == [(c, M.calledBy, me), (c, M.calledOn, v), (me, M.bidsIn, v)]
    assert footprint._patterns(_A_FILTER_IN_A_FILTER) == [(c, M.calledOn, v), (c, M.answered, rdflib.Literal(True)),
                                                           (me, M.bidsIn, v)]


def test_the_market_s_calling_and_tendering_are_read_and_answer_what_they_read():
    """The two shipped texts with both shapes at once (#908): a predicate list under `NOT EXISTS` and
    a `NOT EXISTS` nested in it. Both read anything, so the first defect hid the second, and every
    world of a market agent was hashed whole. Read off the document, not restated here."""
    market = rdflib.Namespace("http://example.org/orexis/market#")
    g = rdflib.Graph().parse(Path(__file__).resolve().parents[3] / "domains" / "market" / "actions.ttl")
    precondition = rdflib.URIRef("http://example.org/orexis/planning#precondition")
    calling, tendering = (str(g.value(market[a], precondition)) for a in ("Calling", "Tendering"))
    assert "FILTER NOT EXISTS { ?call market:calledBy $me ; market:calledOn ?venue ." in calling \
        and "FILTER NOT EXISTS { ?call market:answered true }" in calling, "the text has moved; so has this test's premise"
    assert footprint.reads_of_select(calling) == frozenset(
        {market.bidsIn, market.open, market.calledBy, market.calledOn, market.answered})
    assert footprint.reads_of_select(tendering) == frozenset(
        {market.bidsIn, market.open, market.bidder, market.inRound, market.onVenue, market.clearedAt})


def test_a_shape_whose_select_has_the_two_shapes_reads_their_predicates():
    """The door the constraints and the placing of a want go through (`_constraints`, `_of_scope`):
    a constraint stated as the issue's select was weighed in every world of every scope, since a
    footprint that cannot be read joins everything; it reads its three predicates now."""
    g = rdflib.Graph()
    node = URIRef("urn:test:avoided")
    g.add((node, SH.select, rdflib.Literal(_A_FILTER_IN_A_FILTER.replace("?me", "$this"))))
    assert footprint.reads_of_shape(g, node) == frozenset({M.bidsIn, M.calledOn, M.answered})


def test_what_a_construct_writes_is_its_template_predicates_and_a_variable_one_is_anything():
    assert footprint.writes_of_construct("CONSTRUCT { ?x <urn:test:q> ?v } WHERE { ?x <urn:test:p> ?v }") \
        == frozenset({Q})
    assert footprint.writes_of_construct("CONSTRUCT { ?x ?p ?v } WHERE { ?x ?p ?v }") is footprint.ANYTHING
    assert footprint.writes_of_construct("this is not a query") is footprint.ANYTHING, "unreadable is unfiltered"


def test_a_variable_predicate_a_values_block_bounds_writes_those_and_nothing_more():
    """SPARQL's own range: a template writing `?p` beside `VALUES ?p { a b }` writes two
    predicates, not anything; a block binding another variable bounds nothing, and a row
    leaving it UNDEF unbounds it again."""
    a, b = URIRef("urn:test:a"), URIRef("urn:test:b")
    assert footprint.writes_of_construct(
        "CONSTRUCT { ?x ?p ?v } WHERE { VALUES ?p { <urn:test:a> <urn:test:b> } ?x ?p ?v }") == frozenset({a, b})
    assert footprint.writes_of_construct(
        "CONSTRUCT { ?x ?p ?v . ?x <urn:test:q> ?v } WHERE { VALUES ?p { <urn:test:a> } ?x ?p ?v }") \
        == frozenset({a, URIRef("urn:test:q")})
    assert footprint.writes_of_construct(
        "CONSTRUCT { ?x ?p ?v } WHERE { VALUES ?q { <urn:test:a> } ?x ?p ?v }") is footprint.ANYTHING
    assert footprint.writes_of_construct(
        "CONSTRUCT { ?x ?p ?v } WHERE { VALUES (?p ?r) { (<urn:test:a> <urn:test:b>) (UNDEF <urn:test:b>) } ?x ?p ?v }") \
        is footprint.ANYTHING


def test_a_rule_text_is_made_parseable_and_nothing_more():
    assert "?me" in footprint.parseable("SELECT ?x WHERE { $me <urn:test:p> ?x }")
    assert "$into(" not in footprint.parseable("INSERT { GRAPH $into(x:G) { ?s ?p ?o } } WHERE { ?s ?p ?o }")


def test_what_a_shape_reads_is_its_paths_and_its_target_class():
    g = rdflib.Graph()
    shape, prop = URIRef("urn:test:shape"), rdflib.BNode()
    g.add((shape, RDF.type, SH.NodeShape)); g.add((shape, SH.targetClass, URIRef("urn:test:C")))
    g.add((shape, SH.property, prop)); g.add((prop, SH.path, P)); g.add((prop, SH.minInclusive, rdflib.Literal(10)))
    assert footprint.reads_of_shape(g, shape) == frozenset({P, URIRef("urn:test:C")})


def test_what_an_avoided_state_reads_is_what_its_own_select_reads():
    """The node a `planning:unmetWhen` points at is no shape and carries its select itself (#892);
    its want is placed by what that select reads, and what it is about is a term, `sh:this` apart."""
    g = rdflib.Graph()
    node, about = URIRef("urn:test:avoided"), URIRef("http://example.org/orexis/planning#about")
    g.add((node, SH.select, rdflib.Literal("SELECT $this ?value WHERE { $this <urn:test:p> ?value . ?o <urn:test:q> ?value }")))
    g.add((node, about, SH.this))
    assert footprint.reads_of_shape(g, node) == frozenset({P, Q})
    assert footprint.terms_of_shape(g, node) == frozenset()
    g.set((node, about, P))
    assert footprint.terms_of_shape(g, node) == frozenset({P})


def test_actions_of_reads_every_action_the_store_holds(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(Path(__file__).parent / "plans" / "a_low_tank_is_filled.trig")
    (action,) = footprint.actions_of(store).items()
    iri, (reads, writes) = action
    assert iri.endswith("#fill")
    assert URIRef("http://example.org/test#level") in reads and URIRef("http://example.org/test#level") in writes


def test_stored_edges_read_the_derivations_genesis_wrote(wants):
    update(wants.store, """INSERT DATA {
  GRAPH <urn:test:derivations> {
    <urn:test:d1> a planning:Derivation ; planning:reads <urn:test:p> ; planning:writes <urn:test:q> .
    <urn:test:d2> a planning:Derivation ; planning:reads planning:Anything }
  GRAPH <urn:test:catalogue> { <urn:test:derivations> a planning:DerivationGraph } }""")
    edges = footprint.stored_edges(wants.store, graphs_of(wants.store, DERIVATION_GRAPH))
    assert edges == ((frozenset({P}), frozenset({Q})), (footprint.ANYTHING, frozenset()))

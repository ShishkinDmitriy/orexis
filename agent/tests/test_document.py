"""A document says what its graphs are: `store.document` reads a Turtle file as one graph named by
the file, whose `<>` rows are what it is, and a TriG file as the graphs it names, whose rows sit in
its default graph; `store.put_document` puts the graphs in and the rows in the catalogue, with the
arrival the loader alone says — and the owner, which a world's file may say of a graph of an
agent's own, as a self graph says its self, and which no document from anywhere else may."""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from agent.ontology import CATALOGUE_GRAPH, OREXIS
from agent.store import DocumentRefused, document, document_of, graphs_of, imports_of, kinds_in, put_document, rows, update, whose

PREFIXES = "@prefix orexis: <http://example.org/orexis#> .\n@prefix planning: <http://example.org/orexis/planning#> .\n@prefix dcterms: <http://purl.org/dc/terms/> .\n"
_ROWS_Q = "SELECT ?p ?o WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g ?p ?o } }"


@pytest.fixture
def store():
    st = ox.Store()
    update(st, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph }} }}")
    return st


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(PREFIXES + text)
    return path


def _said(store, graph):
    return {(r["p"].rsplit("#", 1)[-1], r["o"].rsplit("#", 1)[-1]) for r in rows(store, _ROWS_Q, (), g=graph)}


def test_a_turtle_file_is_one_graph_named_by_the_file_and_its_rows_go_to_the_catalogue(store, tmp_path):
    path = _write(tmp_path, "anything.ttl", "<> a orexis:StateGraph .\n<urn:disk> <urn:on> <urn:peg> .\n")
    name = path.resolve().as_uri()
    assert put_document(store, document(path)) == [name]
    assert graphs_of(store, OREXIS + "StateGraph") == [name]
    assert _said(store, name) == {("type", "StateGraph"), ("arrivedBy", "Asserted")}
    held = rows(store, "SELECT ?s ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }", (), g=name)
    assert held == [{"s": "urn:disk", "p": "urn:on", "o": "urn:peg"}], "the graph holds its facts and not its kind"


def test_a_period_stated_of_the_document_goes_with_its_row(store, tmp_path):
    path = _write(tmp_path, "prediction.ttl", """<> a orexis:PredictionGraph ;
    dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start "2026-01-01T00:00:00Z" ] .
<urn:a> <urn:b> <urn:c> .
""")
    (name,) = put_document(store, document(path))
    (row,) = rows(store, """SELECT ?start WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
        $g dcterms:temporal ?period . ?period orexis:start ?start } }""", (), g=name)
    assert row["start"] == "2026-01-01T00:00:00Z"
    assert len(rows(store, "SELECT ?s WHERE { GRAPH $g { ?s ?p ?o } }", (), g=name)) == 1


def test_a_trig_file_names_its_graphs_and_states_their_kinds_in_its_default_graph(store, tmp_path):
    path = _write(tmp_path, "two.trig", """<#desires> a planning:DesireGraph .
<#state> a orexis:StateGraph .
<#desires> { <urn:me> planning:holds <urn:home> . }
<#state> { <urn:disk> <urn:on> <urn:peg> . }
""")
    doc = document(path)
    base = path.resolve().as_uri()
    assert kinds_in(doc) == {base + "#desires": {"http://example.org/orexis/planning#DesireGraph"}, base + "#state": {OREXIS + "StateGraph"}}
    assert put_document(store, doc, owner="urn:me") == sorted([base + "#desires", base + "#state"])
    assert ("beliefsOf", "urn:me") in _said(store, base + "#state")


def test_put_again_replaces_the_graph_and_its_row(store, tmp_path):
    path = _write(tmp_path, "state.ttl", "<> a orexis:StateGraph .\n<urn:disk> <urn:on> <urn:peg_a> .\n")
    put_document(store, document(path))
    path.write_text(PREFIXES + "<> a orexis:WorldGraph .\n<urn:disk> <urn:on> <urn:peg_c> .\n")
    (name,) = put_document(store, document(path))
    assert _said(store, name) == {("type", "WorldGraph"), ("arrivedBy", "Asserted")}
    assert [r["o"] for r in rows(store, "SELECT ?o WHERE { GRAPH $g { ?s ?p ?o } }", (), g=name)] == ["urn:peg_c"]


@pytest.mark.parametrize("text, refusal", [
    ("<urn:a> <urn:b> <urn:c> .\n", "no kind"),
    ("<> a orexis:CatalogueGraph .\n", "catalogue"),
    ("<> a orexis:StateGraph ; orexis:arrivedBy orexis:Derived .\n", "only the loader"),
    ("<> a orexis:StateGraph ; orexis:beliefsOf <urn:ann> , <urn:bob> .\n", "a graph has one owner"),
    ("<> a orexis:StateGraph ; orexis:beliefsOf [] .\n", "an owner is an agent, named"),
    ("<> a orexis:WorldGraph .\n<urn:someone> a orexis:Self .\n", "no self graph"),
    ("<> a orexis:SelfGraph , orexis:WorldGraph .\n<urn:ann> a orexis:Self .\n", "a self graph is nothing else"),
    ("<> a orexis:SelfGraph .\n", "states 0 selves"),
    ("<> a orexis:SelfGraph .\n<urn:ann> a orexis:Self .\n<urn:bob> a orexis:Self .\n", "states 2 selves"),
    ("<> a orexis:SelfGraph ; orexis:beliefsOf <urn:bob> .\n<urn:ann> a orexis:Self .\n", "a self graph is its self's"),
    ("<> a orexis:SelfGraph , orexis:Self .\n<urn:ann> a orexis:Self .\n", "of a graph"),
    ("<> a orexis:WorldGraph .\n<urn:g> a orexis:SelfGraph .\n", "in its rows"),
], ids=["no kind", "the catalogue", "an arrival", "two owners", "an owner unnamed", "a self in a world graph",
        "a self graph that is something else", "a self graph of nobody", "a self graph of two",
        "a self graph owned by another", "a graph that is the self", "a self graph said inside a graph"])
def test_a_file_is_refused_where_it_says_too_little_or_what_only_the_loader_says_or_the_self_twice(tmp_path, text, refusal):
    with pytest.raises(DocumentRefused, match=refusal):
        document(_write(tmp_path, "bad.ttl", text))


def test_a_file_says_whose_its_graph_is_and_a_self_graph_is_its_selfs(tmp_path):
    """What the world authors may say whose a graph is, and its self graph who the self is — the
    owner the boot keeps a graph by, read off the content (`whose`), never the file's name."""
    owned = document(_write(tmp_path, "rose.ttl", "<> a planning:DesireGraph ; orexis:beliefsOf <urn:fern> .\n"))
    assert whose(owned, (tmp_path / "rose.ttl").resolve().as_uri()) == "urn:fern"
    selfish = document(_write(tmp_path, "who.ttl", "<> a orexis:SelfGraph .\n<urn:fern> a orexis:Self .\n"))
    assert whose(selfish, (tmp_path / "who.ttl").resolve().as_uri()) == "urn:fern"
    agreed = document(_write(tmp_path, "both.ttl", "<> a orexis:SelfGraph ; orexis:beliefsOf <urn:fern> .\n<urn:fern> a orexis:Self .\n"))
    assert whose(agreed, (tmp_path / "both.ttl").resolve().as_uri()) == "urn:fern", "one fact, said twice and agreeing"
    nobody = document(_write(tmp_path, "state.ttl", "<> a orexis:StateGraph .\n"))
    assert whose(nobody, (tmp_path / "state.ttl").resolve().as_uri()) is None


@pytest.mark.parametrize("text", [
    "<urn:g> a orexis:StateGraph ; orexis:beliefsOf <urn:someone> .\n<urn:g> { <urn:a> <urn:b> <urn:c> }\n",
    "<urn:g> a orexis:StateGraph .\n<urn:g> { <urn:someone> a orexis:Self }\n",
    "<urn:g> a orexis:SelfGraph .\n<urn:g> { <urn:someone> a orexis:Self }\n",
], ids=["an owner", "who the self is", "the self's graph"])
def test_a_document_from_no_file_says_neither_whose_a_graph_is_nor_who_the_self_is(text):
    """A peer's document, as the transport hands it: the hearer owns what it hears, and no peer tells
    an agent who it is."""
    with pytest.raises(DocumentRefused, match="only the world's own documents say"):
        document_of((PREFIXES + text).encode())


def test_a_trig_row_about_no_graph_the_document_holds_is_refused(tmp_path):
    path = _write(tmp_path, "stray.trig", "<#g> a orexis:StateGraph .\n<urn:x> <urn:y> <urn:z> .\n<#g> { <urn:a> <urn:b> <urn:c> . }\n")
    with pytest.raises(DocumentRefused, match="no graph it holds"):
        document(path)


def test_an_import_by_relative_iri_names_the_graph_the_imported_file_is_loaded_under(tmp_path):
    """`owl:imports <../domain/ontology.ttl>` on the document resolves to the imported file's own
    IRI, which is the name `put_document` gives its graph — so the import names the graph it
    brings, and it is a row about the graph, in the catalogue, not a fact in it."""
    (tmp_path / "domain").mkdir(); (tmp_path / "world").mkdir()
    imported = _write(tmp_path / "domain", "ontology.ttl", "<> a orexis:OntologyGraph .\n")
    path = _write(tmp_path / "world", "world.ttl", "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
                  "<> a orexis:WorldGraph ; owl:imports <../domain/ontology.ttl> .\n")
    doc = document(path)
    assert imports_of(doc) == [imported.resolve().as_uri()]
    assert kinds_in(document(imported)) == {imported.resolve().as_uri(): {OREXIS + "OntologyGraph"}}

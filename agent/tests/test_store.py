"""Engine facts this tree writes its queries around, pinned against the ENGINE itself.

Each is a measured behaviour of pyoxigraph that no test of a READER would report: a reader
that stopped relying on one would go green, and the day the engine grows the operation
nothing would say so. AGENTS.md keeps the list; this holds the ones live queries are shaped by.
"""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from agent.store import bindings, query_over, update


@pytest.fixture
def store():
    return ox.Store()


def test_group_concat_over_an_iri_binds_nothing_and_over_its_string_binds(store):
    """The engine fact three live queries depend on, pinned against the ENGINE rather than
    through a reader that happened to use it.

    `find_wants` grouped a want's several abouts this way and this case pinned it there; a
    want states no abouts now, and the trap does not care — `effects._RULE_Q`, `steps._ACTIONS`
    and `act.BOUND` all still write `STR(?x)` for exactly this reason, and none of them would
    say so if it stopped being true. NOTHING means no column at all: no error, no exception,
    the caller reading an absent key as an empty answer, which is the empty-result trap in its
    purest form (AGENTS.md, the engine-lacks-it list).
    """
    update(store, """INSERT DATA { GRAPH <urn:test:g> {
      <urn:test:s> <urn:test:p> <urn:test:a> , <urn:test:b> . } }""")
    bare = bindings(query_over(store, """
      SELECT (GROUP_CONCAT(?o; separator=" ") AS ?joined) WHERE { ?s <urn:test:p> ?o }""",
                               "urn:test:g"))
    assert "joined" not in bare[0], f"the engine grew it — {bare[0]}; the STR() calls can go"
    strung = bindings(query_over(store, """
      SELECT (GROUP_CONCAT(STR(?o); separator=" ") AS ?joined) WHERE { ?s <urn:test:p> ?o }""",
                                 "urn:test:g"))
    assert sorted(strung[0]["joined"].split()) == ["urn:test:a", "urn:test:b"]


def test_forgetting_a_graph_forgets_the_beliefs_derived_from_it():
    """The revisions of a graph go when it goes. A prediction stretch forgotten for a shorter
    forecast left its revision graph standing with the old side and a period to the old horizon,
    and every possible world of that day read it; the greenhouse's dose read unmet in the world it
    made and the search exhausted until the period ran out."""
    import pyoxigraph as ox

    from agent.store import forget_graph, revisions_of, rows, update

    st = ox.Store()
    update(st, """INSERT DATA {
      GRAPH <urn:cat> { <urn:cat> a orexis:CatalogueGraph .
        <urn:g> a orexis:Graph , orexis:PredictionGraph .
        <urn:g/rev> a orexis:Graph , orexis:BeliefGraph ; prov:wasDerivedFrom <urn:g> .
        <urn:other/rev> a orexis:Graph , orexis:BeliefGraph ; prov:wasDerivedFrom <urn:other> . }
      GRAPH <urn:g> { <urn:s> <urn:p> 1 }
      GRAPH <urn:g/rev> { <urn:s> <urn:side> <urn:below> }
      GRAPH <urn:other/rev> { <urn:s> <urn:side> <urn:inside> } }""")
    assert revisions_of(st, "urn:g") == ["urn:g/rev"]
    forget_graph(st, "urn:g")
    assert revisions_of(st, "urn:g") == []
    assert [r["g"] for r in rows(st, "SELECT ?g WHERE { GRAPH <urn:cat> { ?g a orexis:Graph } } ORDER BY ?g", ())] == ["urn:other/rev"]
    assert rows(st, "SELECT ?o WHERE { GRAPH <urn:g/rev> { ?s ?p ?o } }", ()) == [], "the revision's own quads went too"
    assert rows(st, "SELECT ?o WHERE { GRAPH <urn:other/rev> { ?s ?p ?o } }", ()) != [], "another graph's revision stands"

"""`Wants`, the first repository in the DDD sense — tested where it lives.

**No world, no genesis, no agent.** A repository is BACKED by a store and owns none, so a bare
in-memory store is all one needs to exercise it — and that it suffices is the test's real
finding, because a collection that needed a whole agent to stand up would be a part of one.
`a-package-may-test-itself` draws the line exactly there: eleven tests calling themselves units
took a fixture that built a real agent, and did not qualify.

What is tested is the COLLECTION: that saving a want makes it findable, that finding one by its
desire answers the derivation's question, that deleting it leaves nothing behind, that the
three things `save` writes are all written, and that a write ANNOUNCES itself rather than
deciding what to re-derive. The derivation that uses it is covered end to end by
`tests/test_pursuing.py`.

See knowledge/decisions/a-repository-is-named-for-what-it-holds.md.
"""

from __future__ import annotations

import pytest

from orexis_agent_progression.store import Store, bindings

from orexis_agent_deliberation.want import Want
from orexis_agent_deliberation.derive_wants import forget_want, graph_of, save_want
from orexis_agent_deliberation.wants import Wants

A_DESIRE = "urn:test:gardener.no_overdue_debts"
HOLDER = "urn:test:gardener"
AGENT = "gardener"


@pytest.fixture
def store():
    """A collection over a bare store and NOTHING ELSE — which is the whole point of taking
    one. It took the holder's URI and the agent's id too, until those were seen for what they
    are: another aggregate root's identity, which a collection has no business holding."""
    st = Store()
    #  A catalogue, and the vocabulary's word on what the families are beneath: the collection
    #  asks for graphs of WANTS and of RECORDS, and a pursued graph and an obligations graph
    #  are those by the axioms the packages declare.
    st.update("""INSERT DATA {
  GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph . <urn:test:ontology> a orexis:OntologyGraph }
  GRAPH <urn:test:ontology> { deliberation:PursuedGraph rdfs:subClassOf orexis:WantGraph .
                              market:ObligationsGraph rdfs:subClassOf orexis:RecordGraph } }""")
    return st


@pytest.fixture
def wants(store):
    """The collection, over that store. It reads; the derivation's own functions write."""
    return Wants(store)


def _want(uri="urn:test:want", desire=A_DESIRE, **kw):
    return Want(uri=uri, holder=HOLDER, desire=desire, label="a want under test", **kw)


def _owe(wants, uri):
    """A debt, written the way the LEDGER writes one — its own graph, classified its own family.
    It cannot be written through `save`, which classifies what it writes as the derivation's,
    and that is the point of the case below."""
    graph = f"http://example.org/orexis/market#obligations/gardener/{uri.rsplit(':', 1)[-1]}"
    wants._store.update(f"""INSERT DATA {{
  GRAPH <{graph}> {{ <{uri}> a orexis:Want ; prov:wasDerivedFrom <{A_DESIRE}> ;
      rdfs:label "a debt under test" . }}
  GRAPH <{wants._store.catalogue}> {{ <{graph}> a market:ObligationsGraph , orexis:RecordGraph . }} }}""")


def test_a_saved_want_is_found_and_a_deleted_one_is_not(store, wants):
    """Create, read and delete, on the collection's own terms."""
    assert wants.find_all() == [], "nothing has been derived"

    save_want(store.engine, AGENT, _want())
    found = wants.find_all()
    assert [w.uri for w in found] == ["urn:test:want"]
    assert found[0].desire == A_DESIRE and found[0].label == "a want under test"

    forget_want(store.engine, AGENT, "urn:test:want")
    assert wants.find_all() == [], "and its graph went with it"


def test_forgetting_a_want_leaves_what_replacing_one_leaves(store, wants):
    """The two ways a want goes, held to leaving the same nothing.

    `save_want` replaces a want whole — it drops the graph and the catalogue's account of it
    before inserting — and `forget_want` does the first half and does not put it back. They
    share the text for that reason: a want IS its graph, but what the catalogue says OF that
    graph is not in it, and a row left pointing at an empty graph is litter every reader
    asking by class would still be handed.

    Announcing is nobody's here any more. These write the store and tell no one; whoever
    called says what changed, which is what `pursuit.derived` and `pursuit.withdraw` do.
    """
    save_want(store.engine, AGENT, _want())
    assert wants.find_first_by_uri("urn:test:want") is not None

    forget_want(store.engine, AGENT, "urn:test:want")
    assert wants.find_first_by_uri("urn:test:want") is None, "the want is gone"
    graph = graph_of(AGENT, "urn:test:want")
    assert not bindings(store.query_over(
        f"SELECT ?p WHERE {{ <{graph}> ?p ?o }}", "urn:test:catalogue")), \
        "and the catalogue says nothing of its graph"


def test_a_want_about_several_things_reads_back_about_all_of_them(store, wants):
    """The read path a want about one thing never exercised, and it was broken: the abouts come
    back grouped, and this engine's GROUP_CONCAT over an IRI binds NOTHING — no error, no
    column, every want reading as about nothing. Over `STR(?about)` it binds. Pinned here so
    the day the engine changes its mind, this says so (the engine-lacks-it trap, AGENTS.md)."""
    save_want(store.engine, AGENT, _want(about=("urn:test:air", "urn:test:soil")))
    found = wants.find_first_by_uri("urn:test:want")
    assert found.about == ("urn:test:air", "urn:test:soil"), found.about
    assert wants.find_all()[0].about == found.about, "and the page groups the same way"


def test_a_want_is_found_by_the_desire_it_was_derived_from(store, wants):
    """The derivation's question, asked of the collection rather than written as a query."""
    save_want(store.engine, AGENT, _want())

    assert [w.uri for w in wants.find_all_by_desire(A_DESIRE)] == \
        ["urn:test:want"]
    assert wants.find_first_by_desire(A_DESIRE).uri == "urn:test:want"
    assert wants.find_all_by_desire("urn:test:nobody") == []
    assert wants.find_first_by_desire("urn:test:nobody") is None
    assert wants.find_first_by_uri("urn:test:want").desire == A_DESIRE
    assert wants.find_first_by_uri("urn:test:missing") is None


def test_saving_writes_the_graph_the_classification_and_the_period(store, wants):
    """THREE THINGS, and a caller that had to remember them would remember two. A want IS its
    graph since #645: the classification says which family it belongs to and the period says how
    long it holds, which is what lets the door hide an ended one and one sweep drop it. Written
    without them, a want is invisible to the sweep and outlives its own window."""
    save_want(store.engine, AGENT, _want(holds_at="2026-09-17T12:00:00+00:00",
                     derived_at="2026-09-17T11:00:00+00:00",
                     ends="2026-09-17T12:10:00+00:00"))
    graph = wants.graph_of(AGENT, "urn:test:want")

    kinds = bindings(wants._store.query_union(
        f"SELECT ?t WHERE {{ GRAPH <{wants._store.catalogue}> {{ <{graph}> a ?t }} }}"))
    assert any(r["t"].endswith("PursuedGraph") for r in kinds), "classified as the family it is"

    period = bindings(wants._store.query_union(
        f"SELECT ?s ?e WHERE {{ GRAPH <{wants._store.catalogue}> {{ <{graph}> dcterms:temporal ?p . "
        f"?p orexis:start ?s . OPTIONAL {{ ?p orexis:end ?e }} }} }}"))
    assert period and period[0].get("e", "").startswith("2026-09-17T12:10"), \
        "and it stops holding when its plan's room runs out"


def test_a_want_whose_period_has_closed_is_not_handed_out(store, wants):
    """The part of the door this repository keeps itself. A want IS its graph, so the graph's
    period is the want's; one that has ended is gone to every reader from the instant it ends,
    and not merely from whenever the sweep next runs (#645). The collection binds the graph to
    ask this, which is the one thing it knows that its callers do not."""
    save_want(store.engine, AGENT, _want(uri="urn:test:stale",
                     holds_at="2020-01-01T00:00:00+00:00",
                     derived_at="2020-01-01T00:00:00+00:00",
                     ends="2020-01-01T00:10:00+00:00"))
    assert wants.find_all() == [], "its window closed years ago"
    assert wants.find_first_by_desire(A_DESIRE) is None


def test_a_debt_is_a_want_but_not_one_a_search_is_handed(store, wants):
    """The distinction the collection keeps, and what `find_first_by_desire` scopes by.

    A debt IS a want, typed one, and it is derived from a desire like any other — the ledger
    mints it when a claim arrives rather than when a desire read unmet. What separates it is
    WHOSE it is, and the graph's classification is where that is written. It was a
    binding, `orexis:Within` against `orexis:AtEnd`, which said the difference as a temporal
    fact when what it meant was a family (#681)."""
    save_want(store.engine, AGENT, _want(uri="urn:test:derived"))
    _owe(wants, "urn:test:owed")

    assert {w.uri for w in wants.find_all()} == \
        {"urn:test:derived", "urn:test:owed"}
    assert wants.find_first_by_desire(A_DESIRE).uri == "urn:test:derived", \
        "a search is handed what a desire derived, and never a debt"
    assert {w.uri for w in wants.find_all_by_desire(A_DESIRE)} == \
        {"urn:test:derived", "urn:test:owed"}, \
        "though both name it here"


def test_a_read_is_bounded_and_a_page_is_stable(store, wants, caplog):
    """Every read is capped, and the cap is useless without an order. SPARQL hands back an
    unordered result in whatever order the engine reached it, so `LIMIT` over one picks by
    internal layout — the trap `beliefs.py` records, where a bare `LIMIT 1` read the plant for
    every pick until a load order changed. Ordered, a page walks the collection: the two halves
    of a paged read join back into the whole and share nothing."""
    for n in range(5):
        save_want(store.engine, AGENT, _want(uri=f"urn:test:want{n}"))

    assert len(wants.find_all(limit=2)) == 2, "capped"
    first, second = wants.find_all(limit=3), wants.find_all(limit=3, offset=3)
    assert [w.uri for w in first + second] == [f"urn:test:want{n}" for n in range(5)], \
        "a page walks rather than resamples"
    assert wants.find_all(limit=3) == first, "and answers the same way twice"


def test_a_full_page_is_said_out_loud(store, wants, caplog):
    """Truncating in silence is the empty-result trap wearing a cap: the caller gets a plausible
    answer and no way to know it was cut. Whoever meets the bound either pages or has a leak."""
    for n in range(3):
        save_want(store.engine, AGENT, _want(uri=f"urn:test:want{n}"))

    with caplog.at_level("WARNING"):
        assert len(wants.find_all(limit=3)) == 3
    assert "full page" in caplog.text

    caplog.clear()
    with caplog.at_level("WARNING"):
        wants.find_all(limit=4)
    assert caplog.text == "", "a page with room to spare says nothing"

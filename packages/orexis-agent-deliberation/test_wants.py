"""Reading the wants a store holds — tested where the functions live.

**No world, no genesis, no agent.** A read over a store owns nothing, so a bare in-memory
store is all one needs to exercise it — and that it suffices is the test's real finding,
because a read that needed a whole agent to stand up would be a part of one.
`a-package-may-test-itself` draws the line exactly there: eleven tests calling themselves units
took a fixture that built a real agent, and did not qualify.

What is tested is the READ: that saving a want makes it findable, that finding one by its
desire answers the derivation's question, that deleting it leaves nothing behind, that the
three things `save_want` writes are all written, and that an ended one is handed to nobody.
The derivation that uses it is covered end to end by `tests/test_considering.py`.

This was `Wants`, a class holding one attribute. What it bought — the graph names and the
query text stop being things a caller knows — the module buys, and the five finders it
carried were one query with a criterion swapped.
"""

from __future__ import annotations

import pytest

from orexis_agent_progression.store import Store, bindings

from orexis_agent_deliberation.want import Want
from orexis_agent_deliberation.derive_wants import graph_of, save_want
from orexis_agent_deliberation.forget_wants import forget_want
from orexis_agent_deliberation.wants import find_want, find_wants

A_DESIRE = "urn:test:gardener.no_overdue_debts"
HOLDER = "urn:test:gardener"
AGENT = "gardener"


@pytest.fixture
def store():
    """A bare store and NOTHING ELSE — which is the whole point of handing one in. The read
    took the holder's URI and the agent's id too, until those were seen for what they are:
    another aggregate root's identity, which a read over a store has no business holding.
    Whose the wants are is the store's own (rule 4: one agent, one volume)."""
    st = Store()
    #  A catalogue, and the vocabulary's word on what a record is beneath: the read asks for
    #  graphs of WANTS and of RECORDS, and an obligations graph is one by the axiom the market
    #  declares. The derivation's own graphs need no axiom — they ARE graphs of wants, and
    #  that the derivation wrote them is `orexis:arrivedBy` rather than a class.
    st.update("""INSERT DATA {
  GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph . <urn:test:ontology> a orexis:OntologyGraph }
  GRAPH <urn:test:ontology> { market:ObligationsGraph rdfs:subClassOf orexis:RecordGraph } }""")
    return st


def _want(uri="urn:test:want", desire=A_DESIRE, **kw):
    return Want(uri=uri, holder=HOLDER, desire=desire, label="a want under test", **kw)


def _owe(store, uri):
    """A debt, written the way the LEDGER writes one — its own graph, classified its own family.
    It cannot be written through `save`, which classifies what it writes as the derivation's,
    and that is the point of the case below."""
    graph = f"http://example.org/orexis/market#obligations/gardener/{uri.rsplit(':', 1)[-1]}"
    store.update(f"""INSERT DATA {{
  GRAPH <{graph}> {{ <{uri}> a orexis:Want ; prov:wasDerivedFrom <{A_DESIRE}> ;
      rdfs:label "a debt under test" . }}
  GRAPH <{store.catalogue}> {{ <{graph}> a market:ObligationsGraph , orexis:RecordGraph . }} }}""")


def test_a_saved_want_is_found_and_a_deleted_one_is_not(store):
    """Create, read and delete, through the functions that do each."""
    assert find_wants(store) == [], "nothing has been derived"

    save_want(store.engine, AGENT, _want())
    found = find_wants(store)
    assert [w.uri for w in found] == ["urn:test:want"]
    assert found[0].desire == A_DESIRE and found[0].label == "a want under test"

    forget_want(store.engine, "urn:test:want")
    assert find_wants(store) == [], "and its graph went with it"


def test_forgetting_a_want_leaves_what_replacing_one_leaves(store):
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
    assert find_want(store, uri="urn:test:want") is not None

    forget_want(store.engine, "urn:test:want")
    assert find_want(store, uri="urn:test:want") is None, "the want is gone"
    graph = graph_of(AGENT, "urn:test:want")
    assert not bindings(store.query_over(
        f"SELECT ?p WHERE {{ <{graph}> ?p ?o }}", "urn:test:catalogue")), \
        "and the catalogue says nothing of its graph"


def test_a_want_about_several_things_reads_back_about_all_of_them(store):
    """The read path a want about one thing never exercised, and it was broken: the abouts come
    back grouped, and this engine's GROUP_CONCAT over an IRI binds NOTHING — no error, no
    column, every want reading as about nothing. Over `STR(?about)` it binds. Pinned here so
    the day the engine changes its mind, this says so (the engine-lacks-it trap, AGENTS.md)."""
    save_want(store.engine, AGENT, _want(about=("urn:test:air", "urn:test:soil")))
    found = find_want(store, uri="urn:test:want")
    assert found.about == ("urn:test:air", "urn:test:soil"), found.about
    assert find_wants(store)[0].about == found.about, "and the page groups the same way"


def test_a_want_is_found_by_the_desire_it_was_derived_from(store):
    """The derivation's question, asked as a criterion rather than written as a query."""
    save_want(store.engine, AGENT, _want())

    assert [w.uri for w in find_wants(store, desire=A_DESIRE)] == \
        ["urn:test:want"]
    assert find_want(store, desire=A_DESIRE, derived=True).uri == "urn:test:want"
    assert find_wants(store, desire="urn:test:nobody") == []
    assert find_want(store, desire="urn:test:nobody", derived=True) is None
    assert find_want(store, uri="urn:test:want").desire == A_DESIRE
    assert find_want(store, uri="urn:test:missing") is None


def test_saving_writes_the_graph_the_classification_and_the_period(store):
    """THREE THINGS, and a caller that had to remember them would remember two. A want IS its
    graph since #645: the classification says which family it belongs to and the period says how
    long it holds, which is what lets the door hide an ended one and one sweep drop it. Written
    without them, a want is invisible to the sweep and outlives its own window."""
    save_want(store.engine, AGENT, _want(holds_at="2026-09-17T12:00:00+00:00",
                     derived_at="2026-09-17T11:00:00+00:00",
                     ends="2026-09-17T12:10:00+00:00"))
    graph = graph_of(AGENT, "urn:test:want")

    kinds = bindings(store.query_union(
        f"SELECT ?t ?a WHERE {{ GRAPH <{store.catalogue}> {{ <{graph}> a ?t . "
        f"OPTIONAL {{ <{graph}> orexis:arrivedBy ?a }} }} }}"))
    assert any(r["t"].endswith("WantGraph") for r in kinds), "classified by what it HOLDS"
    #  AND ON THE OTHER AXIS, separately: that the derivation rather than a world put the rows
    #  there. It was one class saying both (`deliberation:PursuedGraph`), which is the thing
    #  agent/ontology.ttl forbids a content class to do, and it cost a read for the world's
    #  own wants — there was no way to ask for a graph of wants without asking whose it was.
    assert any(r.get("a", "").endswith("#Derived") for r in kinds), "and by how it ARRIVED"

    period = bindings(store.query_union(
        f"SELECT ?s ?e WHERE {{ GRAPH <{store.catalogue}> {{ <{graph}> dcterms:temporal ?p . "
        f"?p orexis:start ?s . OPTIONAL {{ ?p orexis:end ?e }} }} }}"))
    assert period and period[0].get("e", "").startswith("2026-09-17T12:10"), \
        "and it stops holding when its plan's room runs out"


def test_a_want_whose_period_has_closed_is_not_handed_out(store):
    """The part of the door this read keeps itself. A want IS its graph, so the graph's
    period is the want's; one that has ended is gone to every reader from the instant it ends,
    and not merely from whenever the sweep next runs (#645). The read binds the graph to ask
    this, which is the one thing it knows that its callers do not."""
    save_want(store.engine, AGENT, _want(uri="urn:test:stale",
                     holds_at="2020-01-01T00:00:00+00:00",
                     derived_at="2020-01-01T00:00:00+00:00",
                     ends="2020-01-01T00:10:00+00:00"))
    assert find_wants(store) == [], "its window closed years ago"
    assert find_want(store, desire=A_DESIRE, derived=True) is None


def test_a_debt_is_a_want_but_not_one_a_search_is_handed(store):
    """The distinction the read keeps, and what `derived=True` scopes by.

    A debt IS a want, typed one, and it is derived from a desire like any other — the ledger
    mints it when a claim arrives rather than when a desire read unmet. What separates it is
    WHOSE it is, and the graph's classification is where that is written. It was a
    binding, `orexis:Within` against `orexis:AtEnd`, which said the difference as a temporal
    fact when what it meant was a family (#681)."""
    save_want(store.engine, AGENT, _want(uri="urn:test:derived"))
    _owe(store, "urn:test:owed")

    assert {w.uri for w in find_wants(store)} == \
        {"urn:test:derived", "urn:test:owed"}
    assert find_want(store, desire=A_DESIRE, derived=True).uri == "urn:test:derived", \
        "a search is handed what a desire derived, and never a debt"
    assert {w.uri for w in find_wants(store, desire=A_DESIRE)} == \
        {"urn:test:derived", "urn:test:owed"}, \
        "though both name it here"


def test_a_read_is_bounded_and_a_page_is_stable(store, caplog):
    """Every read is capped, and the cap is useless without an order. SPARQL hands back an
    unordered result in whatever order the engine reached it, so `LIMIT` over one picks by
    internal layout — the trap `beliefs.py` records, where a bare `LIMIT 1` read the plant for
    every pick until a load order changed. Ordered, a page walks the wants: the two halves
    of a paged read join back into the whole and share nothing."""
    for n in range(5):
        save_want(store.engine, AGENT, _want(uri=f"urn:test:want{n}"))

    assert len(find_wants(store, limit=2)) == 2, "capped"
    first, second = find_wants(store, limit=3), find_wants(store, limit=3, offset=3)
    assert [w.uri for w in first + second] == [f"urn:test:want{n}" for n in range(5)], \
        "a page walks rather than resamples"
    assert find_wants(store, limit=3) == first, "and answers the same way twice"


def test_a_full_page_is_said_out_loud(store, caplog):
    """Truncating in silence is the empty-result trap wearing a cap: the caller gets a plausible
    answer and no way to know it was cut. Whoever meets the bound either pages or has a leak."""
    for n in range(3):
        save_want(store.engine, AGENT, _want(uri=f"urn:test:want{n}"))

    with caplog.at_level("WARNING"):
        assert len(find_wants(store, limit=3)) == 3
    assert "full page" in caplog.text

    caplog.clear()
    with caplog.at_level("WARNING"):
        find_wants(store, limit=4)
    assert caplog.text == "", "a page with room to spare says nothing"

"""Reading the wants a store holds — tested where the functions live.

**No world, no genesis, no agent.** A read over a store owns nothing, so a bare in-memory
store is all one needs to exercise it — and that it suffices is the test's real finding,
because a read that needed a whole agent to stand up would be a part of one.
`a-package-may-test-itself` draws the line exactly there: eleven tests calling themselves units
took a fixture that built a real agent, and did not qualify.

What is tested is the READ, and only the read: that a want written the way the derivation
writes one is findable, that finding one by its desire answers the derivation's question, that
deleting it leaves nothing behind, and that an ended one is handed to nobody. The rows are
written HERE (`_derived` below) rather than through the derivation's own writer, so the read is
not being tested against the writer — a matching pair of mistakes would pass. That the writer
still produces these rows is what `tests/derive_wants/` says, case by case.

This was `Wants`, a class holding one attribute. What it bought — the graph names and the
query text stop being things a caller knows — the module buys, and the five finders it
carried were one query with a criterion swapped.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import pyoxigraph as ox

from orexis.agent.store import (bindings, catalogue_of, query_over,
                                          query_union, update)

from orexis.agent.planning.derive_wants import graph_of
from orexis.agent.planning.forget_wants import forget_want
from orexis.agent.planning.wants import find_want, find_wants

A_DESIRE = "urn:test:gardener.no_overdue_debts"
HOLDER = "urn:test:gardener"
AGENT = "gardener"
#  WHEN THE WRITE HAPPENS. A want's period starts at the instant it was derived, and that
#  instant is the caller's — so a test says it rather than patching a clock.
NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def store():
    """A bare store and NOTHING ELSE — which is the whole point of handing one in. The read
    took the holder's URI and the agent's id too, until those were seen for what they are:
    another aggregate root's identity, which a read over a store has no business holding.
    Whose the wants are is the store's own (rule 4: one agent, one volume)."""
    st = ox.Store()
    #  A catalogue, and the vocabulary's word on what a record is beneath: the read asks for
    #  graphs of WANTS and of RECORDS, and an obligations graph is one by the axiom the market
    #  declares. The derivation's own graphs need no axiom — they ARE graphs of wants, and
    #  that the derivation wrote them is `orexis:arrivedBy` rather than a class.
    update(st, """INSERT DATA {
  GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph . <urn:test:ontology> a orexis:OntologyGraph }
  GRAPH <urn:test:ontology> { <urn:test:ObligationsGraph> rdfs:subClassOf orexis:RecordGraph } }""")
    return st


def _derived(store, uri="urn:test:want", desire=A_DESIRE, *, at=NOW, until=None, side=None):
    """A want, written the way the DERIVATION writes one — a graph of wants that arrived
    derived, whose PERIOD IS THE STRETCH the trouble occupies, and provenance saying when the
    agent found it.

    WRITTEN HERE AND NOT THROUGH THE WRITER. `derive_wants` has a private `_write`, and these
    cases are about the READ: seeding them through the writer would test the two against each
    other, so a matching pair of mistakes would pass. The rows below are what `find_wants`
    claims to be able to read, said plainly, and if the writer stops producing them the
    snapshot cases in `tests/derive_wants/` are what say so.
    """
    graph = graph_of(AGENT, at, until)
    broke = f" ; orexis:violationIs <{side}>" if side else ""
    period = f' ; orexis:start "{at.isoformat()}"^^xsd:dateTime' + (
        f' ; orexis:end "{until.isoformat()}"^^xsd:dateTime' if until else "")
    update(store, f"""INSERT DATA {{
  GRAPH <{graph}> {{
    <{HOLDER}> orexis:holds <{uri}> .
    <{uri}> a orexis:Want{broke} ;
        prov:generatedAtTime "{NOW.isoformat()}"^^xsd:dateTime ;
        prov:wasDerivedFrom <{desire}> ;
        rdfs:label "a want under test" . }}
  GRAPH <{catalogue_of(store)}> {{
    <{graph}> a orexis:WantGraph , orexis:Graph ; orexis:arrivedBy orexis:Derived ;
        orexis:beliefsOf <{HOLDER}> . }} }}""")
    #  THE PERIOD ONCE PER GRAPH, and this guard is the writer's own. A period is a BLANK NODE
    #  and a blank node in an `INSERT` is a new node every time it runs; several wants share a
    #  stretch's graph now, so asserting it per want gave the graph a period per want and every
    #  read joining through `dcterms:temporal` returned each want once per period.
    update(store, f"""
INSERT {{ GRAPH <{catalogue_of(store)}> {{ <{graph}> dcterms:temporal
      [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE  {{ GRAPH <{catalogue_of(store)}> {{ }}
          FILTER NOT EXISTS {{ GRAPH <{catalogue_of(store)}> {{ <{graph}> dcterms:temporal ?h }} }} }}""")


def _owe(store, uri):
    """A debt, written the way a LEDGER writes one — its own graph, classified its own family.

    THE FAMILY IS THIS CASE'S OWN WORD, not a package's. It was `market:ObligationsGraph`, and
    that prefix reached the store because the 1.0 assembly walked `packages/` and merged every
    ontology it found. This tree reads its own, so a package's word is not in its dictionary —
    which is the point of the tree being liftable, and which this case is the only thing that
    noticed. What the case is ABOUT is a record graph some package owns; which package is not
    part of the claim.
    It cannot be written through `save`, which classifies what it writes as the derivation's,
    and that is the point of the case below."""
    graph = f"http://example.org/orexis/market#obligations/gardener/{uri.rsplit(':', 1)[-1]}"
    update(store, f"""INSERT DATA {{
  GRAPH <{graph}> {{ <{uri}> a orexis:Want ; prov:wasDerivedFrom <{A_DESIRE}> ;
      rdfs:label "a debt under test" . }}
  GRAPH <{catalogue_of(store)}> {{ <{graph}> a <urn:test:ObligationsGraph> , orexis:RecordGraph . }} }}""")


def test_a_saved_want_is_found_and_a_deleted_one_is_not(store):
    """Create, read and delete, through the functions that do each."""
    assert find_wants(store) == [], "nothing has been derived"

    _derived(store)
    found = find_wants(store)
    assert [w.uri for w in found] == ["urn:test:want"]
    assert found[0].desire == A_DESIRE and found[0].label == "a want under test"

    forget_want(store, "urn:test:want")
    assert find_wants(store) == [], "and its graph went with it"


def test_forgetting_a_want_leaves_what_replacing_one_leaves(store):
    """The two ways a want goes, held to leaving the same nothing.

    The derivation takes a want out and puts it back; `forget_want` does the first half and
    does not put it back. They share the text for that reason. What the catalogue says OF the
    graph is not in the graph, so a row left pointing at an empty one is litter every reader
    asking by class would still be handed — and a graph is taken away only when the want was
    the LAST in it, since a stretch is shared by whatever is in trouble over it.

    Announcing is nobody's here any more. These write the store and tell no one; whoever
    called says what changed, so a caller holding a projection can refresh it.
    """
    _derived(store)
    assert find_want(store, uri="urn:test:want") is not None

    forget_want(store, "urn:test:want")
    assert find_want(store, uri="urn:test:want") is None, "the want is gone"
    graph = graph_of(AGENT, NOW, None)
    assert not bindings(query_over(store, 
        f"SELECT ?p WHERE {{ <{graph}> ?p ?o }}", "urn:test:catalogue")), \
        "and the catalogue says nothing of its graph"


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


def test_a_want_is_found_by_the_desire_it_was_derived_from(store):
    """The derivation's question, asked as a criterion rather than written as a query."""
    _derived(store)

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
    lifts = datetime(2026, 9, 17, 12, 10, tzinfo=timezone.utc)
    _derived(store, until=lifts)
    graph = graph_of(AGENT, NOW, lifts)

    kinds = bindings(query_union(store, 
        f"SELECT ?t ?a WHERE {{ GRAPH <{catalogue_of(store)}> {{ <{graph}> a ?t . "
        f"OPTIONAL {{ <{graph}> orexis:arrivedBy ?a }} }} }}"))
    assert any(r["t"].endswith("WantGraph") for r in kinds), "classified by what it HOLDS"
    #  AND ON THE OTHER AXIS, separately: that the derivation rather than a world put the rows
    #  there. One class used to say both, which is the thing the kernel vocabulary forbids a
    #  content class to do, and it cost a read for the world's own wants — there was no way to
    #  ask for a graph of wants without asking whose it was.
    assert any(r.get("a", "").endswith("#Derived") for r in kinds), "and by how it ARRIVED"

    period = bindings(query_union(store, 
        f"SELECT ?s ?e WHERE {{ GRAPH <{catalogue_of(store)}> {{ <{graph}> dcterms:temporal ?p . "
        f"?p orexis:start ?s . OPTIONAL {{ ?p orexis:end ?e }} }} }}"))
    assert period and period[0].get("e", "").startswith("2026-09-17T12:10"), \
        "and it stops holding when the world says its trouble lifts"


def test_a_want_whose_period_has_closed_is_not_handed_out(store):
    """The part of the door this read keeps itself. A want IS its graph, so the graph's
    period is the want's; one that has ended is gone to every reader from the instant it ends,
    and not merely from whenever the sweep next runs (#645). The read binds the graph to ask
    this, which is the one thing it knows that its callers do not."""
    _derived(store, uri="urn:test:stale", at=datetime(2020, 1, 1, tzinfo=timezone.utc),
             until=datetime(2020, 1, 1, 0, 10, tzinfo=timezone.utc))
    assert find_wants(store) == [], "its window closed years ago"
    assert find_want(store, desire=A_DESIRE, derived=True) is None


def test_a_debt_is_a_want_but_not_one_a_search_is_handed(store):
    """The distinction the read keeps, and what `derived=True` scopes by.

    A debt IS a want, typed one, and it is derived from a desire like any other — the ledger
    mints it when a claim arrives rather than when a desire read unmet. What separates it is
    WHOSE it is, and the graph's classification is where that is written. It was a
    binding, `orexis:Within` against `orexis:AtEnd`, which said the difference as a temporal
    fact when what it meant was a family (#681)."""
    _derived(store, uri="urn:test:derived")
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
        _derived(store, uri=f"urn:test:want{n}")

    assert len(find_wants(store, limit=2)) == 2, "capped"
    first, second = find_wants(store, limit=3), find_wants(store, limit=3, offset=3)
    assert [w.uri for w in first + second] == [f"urn:test:want{n}" for n in range(5)], \
        "a page walks rather than resamples"
    assert find_wants(store, limit=3) == first, "and answers the same way twice"


def test_a_full_page_is_said_out_loud(store, caplog):
    """Truncating in silence is the empty-result trap wearing a cap: the caller gets a plausible
    answer and no way to know it was cut. Whoever meets the bound either pages or has a leak."""
    for n in range(3):
        _derived(store, uri=f"urn:test:want{n}")

    with caplog.at_level("WARNING"):
        assert len(find_wants(store, limit=3)) == 3
    assert "full page" in caplog.text

    caplog.clear()
    with caplog.at_level("WARNING"):
        find_wants(store, limit=4)
    assert caplog.text == "", "a page with room to spare says nothing"

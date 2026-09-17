"""`Wants`, the first repository in the DDD sense — tested where it lives.

**No world, no genesis, no agent.** A repository is BACKED by a store and owns none, so a bare
in-memory store is all one needs to exercise it — and that it suffices is the test's real
finding, because a collection that needed a whole agent to stand up would be a part of one.
`a-package-may-test-itself` draws the line exactly there: eleven tests calling themselves units
took a fixture that built a real agent, and did not qualify.

What is tested is the COLLECTION: that saving a want makes it findable, that finding one by its
desire answers the pursuit road's question, that deleting it leaves nothing behind, that the
three things `save` writes are all written, and that a write ANNOUNCES itself rather than
deciding what to re-derive. The road that uses it is covered end to end by `tests/test_pursued.py`.

See knowledge/decisions/a-repository-is-named-for-what-it-holds.md.
"""

from __future__ import annotations

import pytest

from orexis_agent_progression.ontology import CLASSIFICATION_GRAPH, PERIODS_GRAPH
from orexis_agent_progression.store import Store, bindings

from orexis_agent_deliberation.want import Want
from orexis_agent_deliberation.wants import Wants

A_DESIRE = "urn:test:gardener.no_overdue_debts"
HOLDER = "urn:test:gardener"


@pytest.fixture
def wants():
    """A collection over a bare store — which is the whole point of taking one."""
    return Wants(Store(), HOLDER, "gardener")


def _want(uri="urn:test:want", desire=A_DESIRE, binds="orexis:AtEnd", **kw):
    return Want(uri=uri, desire=desire, binds=binds, label="a want under test", **kw)


def test_a_saved_want_is_found_and_a_deleted_one_is_not(wants):
    """Create, read and delete, on the collection's own terms."""
    assert wants.find_all() == [], "nothing has been derived"

    wants.save(_want())
    found = wants.find_all()
    assert [w.uri for w in found] == ["urn:test:want"]
    assert found[0].desire == A_DESIRE and found[0].label == "a want under test"

    wants.delete_by_uri("urn:test:want")
    assert wants.find_all() == [], "and its graph went with it"


def test_a_write_announces_itself_and_re_derives_nothing(wants):
    """The asymmetry this class absorbs, and the half it refuses to take on. A want is written
    to a store the desire modality PROJECTS, so a write leaves that projection stale and a
    reader of it sees nothing — which is why every writer used to rebuild by hand. Being told
    is the collection's job; deciding what a write invalidated is the assembler's, so what is
    tested here is that the announcement happens and that nothing else is presumed."""
    saved, deleted = [], []
    wants.on_saved.append(saved.append)
    wants.on_deleted.append(deleted.append)

    wants.save(_want())
    assert [w.uri for w in saved] == ["urn:test:want"], "told what was saved"
    wants.delete_by_uri("urn:test:want")
    assert deleted == ["urn:test:want"], "and which one went"


def test_a_want_is_found_by_the_desire_it_was_derived_from(wants):
    """The pursuit road's question, asked of the collection rather than written as a query."""
    wants.save(_want())

    assert [w.uri for w in wants.find_all_by_desire(A_DESIRE)] == \
        ["urn:test:want"]
    assert wants.find_first_by_desire(A_DESIRE).uri == "urn:test:want"
    assert wants.find_all_by_desire("urn:test:nobody") == []
    assert wants.find_first_by_desire("urn:test:nobody") is None
    assert wants.find_first_by_uri("urn:test:want").binds.endswith("AtEnd")
    assert wants.find_first_by_uri("urn:test:missing") is None


def test_saving_writes_the_graph_the_classification_and_the_period(wants):
    """THREE THINGS, and a caller that had to remember them would remember two. A want IS its
    graph since #645: the classification says which family it belongs to and the period says how
    long it holds, which is what lets the door hide an ended one and one sweep drop it. Written
    without them, a want is invisible to the sweep and outlives its own window."""
    wants.save(_want(holds_at="2026-09-17T12:00:00+00:00",
                     derived_at="2026-09-17T11:00:00+00:00",
                     ends="2026-09-17T12:10:00+00:00"))
    graph = wants.graph_of("urn:test:want")

    kinds = bindings(wants._store.query_union(
        f"SELECT ?t WHERE {{ GRAPH <{CLASSIFICATION_GRAPH}> {{ <{graph}> a ?t }} }}"))
    assert any(r["t"].endswith("PursuedGraph") for r in kinds), "classified as the family it is"

    period = bindings(wants._store.query_union(
        f"SELECT ?s ?e WHERE {{ GRAPH <{PERIODS_GRAPH}> {{ <{graph}> dcterms:temporal ?p . "
        f"?p orexis:start ?s . OPTIONAL {{ ?p orexis:end ?e }} }} }}"))
    assert period and period[0].get("e", "").startswith("2026-09-17T12:10"), \
        "and it stops holding when its plan's room runs out"


def test_a_want_whose_period_has_closed_is_not_handed_out(wants):
    """The part of the door this repository keeps itself. A want IS its graph, so the graph's
    period is the want's; one that has ended is gone to every reader from the instant it ends,
    and not merely from whenever the sweep next runs (#645). The collection binds the graph to
    ask this, which is the one thing it knows that its callers do not."""
    wants.save(_want(uri="urn:test:stale",
                     holds_at="2020-01-01T00:00:00+00:00",
                     derived_at="2020-01-01T00:00:00+00:00",
                     ends="2020-01-01T00:10:00+00:00"))
    assert wants.find_all() == [], "its window closed years ago"
    assert wants.find_first_by_desire(A_DESIRE) is None


def test_a_debt_is_a_want_but_not_one_a_search_is_handed(wants):
    """The distinction the collection keeps, and why `find_first_by_desire` filters. A debt IS a
    want — typed one, carrying a period — but it binds `orexis:Within` and the ledger mints it
    when a claim arrives, not when a desire read unmet. So it is in `find_all` and it is not
    what the pursuit road finds under a desire. The two roads meet at #675 and not before."""
    wants.save(_want(uri="urn:test:derived"))
    wants.save(_want(uri="urn:test:owed", binds="orexis:Within"))

    assert {w.uri for w in wants.find_all()} == \
        {"urn:test:derived", "urn:test:owed"}
    assert wants.find_first_by_desire(A_DESIRE).uri == "urn:test:derived", \
        "a search is handed what a desire derived, and never a debt"
    assert {w.uri for w in wants.find_all_by_desire(A_DESIRE)} == \
        {"urn:test:derived", "urn:test:owed"}, \
        "though both name it here"


def test_a_read_is_bounded_and_a_page_is_stable(wants, caplog):
    """Every read is capped, and the cap is useless without an order. SPARQL hands back an
    unordered result in whatever order the engine reached it, so `LIMIT` over one picks by
    internal layout — the trap `beliefs.py` records, where a bare `LIMIT 1` read the plant for
    every pick until a load order changed. Ordered, a page walks the collection: the two halves
    of a paged read join back into the whole and share nothing."""
    for n in range(5):
        wants.save(_want(uri=f"urn:test:want{n}"))

    assert len(wants.find_all(limit=2)) == 2, "capped"
    first, second = wants.find_all(limit=3), wants.find_all(limit=3, offset=3)
    assert [w.uri for w in first + second] == [f"urn:test:want{n}" for n in range(5)], \
        "a page walks rather than resamples"
    assert wants.find_all(limit=3) == first, "and answers the same way twice"


def test_a_full_page_is_said_out_loud(wants, caplog):
    """Truncating in silence is the empty-result trap wearing a cap: the caller gets a plausible
    answer and no way to know it was cut. Whoever meets the bound either pages or has a leak."""
    for n in range(3):
        wants.save(_want(uri=f"urn:test:want{n}"))

    with caplog.at_level("WARNING"):
        assert len(wants.find_all(limit=3)) == 3
    assert "full page" in caplog.text

    caplog.clear()
    with caplog.at_level("WARNING"):
        wants.find_all(limit=4)
    assert caplog.text == "", "a page with room to spare says nothing"

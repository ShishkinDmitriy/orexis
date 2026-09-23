"""Reading the wants a store holds — tested where the function lives.

What is tested is the READ, and only the read: that a want written the way the derivation
writes one is findable, that finding one by its desire answers the derivation's question, that
an ended one is handed to nobody, and that a page is bounded and stable. The rows come from the
`wants` fixture rather than from the derivation's own writer, so the read is not being tested
against the writer that seeds it — a matching pair of mistakes would pass.

This was `test_wants.py`, beside a `wants.py`, which was beside a `Wants` class holding one
attribute. The read is one function in a module named for it now, `find_wants.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agent.planning.find_wants import find_wants
from agent.planning.withdraw import withdraw


def test_a_saved_want_is_found_and_a_deleted_one_is_not(wants):
    """Create, read and withdraw, through the functions that do each."""
    assert find_wants(wants.store) == [], "nothing has been derived"

    wants.derived()
    #  THE URI AND NOTHING ELSE. What the derivation WROTE beside it — the label, the desire
    #  it came from, the side that broke — is held by `test_derive_wants.py`, against the
    #  whole store a derivation leaves rather than against a reading of it. This read answers
    #  which wants are there.
    assert find_wants(wants.store) == ["urn:test:want"]

    withdraw(wants.store, set(), wants.at)
    assert find_wants(wants.store) == [], "and its graph went with it"


def test_a_want_is_found_by_the_desire_it_was_derived_from(wants):
    """The derivation's question, asked as a criterion rather than written as a query."""
    wants.derived()

    assert find_wants(wants.store, desire=wants.desire) == ["urn:test:want"]
    assert find_wants(wants.store, desire=wants.desire, derived=True) == ["urn:test:want"]
    assert find_wants(wants.store, desire="urn:test:nobody") == []
    assert find_wants(wants.store, desire="urn:test:nobody", derived=True) == []
    assert find_wants(wants.store, uri="urn:test:want") == ["urn:test:want"]
    assert find_wants(wants.store, uri="urn:test:missing") == []


def test_a_want_whose_period_has_closed_is_not_handed_out(wants):
    """The part of the door this read keeps itself. A want IS its graph, so the graph's
    period is the want's; one that has ended is gone to every reader from the instant it ends,
    and not merely from whenever the sweep next runs (#645). The read binds the graph to ask
    this, which is the one thing it knows that its callers do not."""
    wants.derived(uri="urn:test:stale", at=datetime(2020, 1, 1, tzinfo=timezone.utc),
             until=datetime(2020, 1, 1, 0, 10, tzinfo=timezone.utc))
    assert find_wants(wants.store) == [], "its window closed years ago"
    assert find_wants(wants.store, desire=wants.desire, derived=True) == []


def test_a_debt_is_a_want_but_not_one_a_search_is_handed(wants):
    """The distinction the read keeps, and what `derived=True` scopes by.

    A debt IS a want, typed one, and it is derived from a desire like any other — the ledger
    mints it when a claim arrives rather than when a desire read unmet. What separates it is
    WHOSE it is, and the graph's classification is where that is written. It was a
    binding, `orexis:Within` against `orexis:AtEnd`, which said the difference as a temporal
    fact when what it meant was a family (#681)."""
    wants.derived(uri="urn:test:derived")
    wants.owed("urn:test:owed")

    assert set(find_wants(wants.store)) == {"urn:test:derived", "urn:test:owed"}
    assert find_wants(wants.store, desire=wants.desire, derived=True) == ["urn:test:derived"], \
        "a search is handed what a desire derived, and never a debt"
    assert set(find_wants(wants.store, desire=wants.desire)) == \
        {"urn:test:derived", "urn:test:owed"}, \
        "though both name it here"


def test_a_read_is_bounded_and_a_page_is_stable(wants, caplog):
    """Every read is capped, and the cap is useless without an order. SPARQL hands back an
    unordered result in whatever order the engine reached it, so `LIMIT` over one picks by
    internal layout — the trap `beliefs.py` records, where a bare `LIMIT 1` read the plant for
    every pick until a load order changed. Ordered, a page walks the wants: the two halves
    of a paged read join back into the whole and share nothing."""
    for n in range(5):
        wants.derived(uri=f"urn:test:want{n}")

    assert len(find_wants(wants.store, limit=2)) == 2, "capped"
    first, second = find_wants(wants.store, limit=3), find_wants(wants.store, limit=3, offset=3)
    assert first + second == [f"urn:test:want{n}" for n in range(5)], \
        "a page walks rather than resamples"
    assert find_wants(wants.store, limit=3) == first, "and answers the same way twice"


def test_a_full_page_is_said_out_loud(wants, caplog):
    """Truncating in silence is the empty-result trap wearing a cap: the caller gets a plausible
    answer and no way to know it was cut. Whoever meets the bound either pages or has a leak."""
    for n in range(3):
        wants.derived(uri=f"urn:test:want{n}")

    with caplog.at_level("WARNING"):
        assert len(find_wants(wants.store, limit=3)) == 3
    assert "full page" in caplog.text

    caplog.clear()
    with caplog.at_level("WARNING"):
        find_wants(wants.store, limit=4)
    assert caplog.text == "", "a page with room to spare says nothing"

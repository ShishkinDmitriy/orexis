"""Forking a graph — the store's primitive, tested where it lives.

The order is the whole of the function: copy, every delete, then the adds — and the copy and
the deletes reach the engine as one text, with each retraction's own `PREFIX` hoisted to the
head, because the engine refuses a prologue after a `;`.
"""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from orexis.agent.store import fork, quads, update

S, LEVEL, TEMP = ox.NamedNode("urn:test:s"), ox.NamedNode("urn:test:level"), ox.NamedNode("urn:test:temp")


def _lit(n):
    return ox.Literal(str(n), datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer"))


@pytest.fixture
def store():
    st = ox.Store()
    update(st, 'INSERT DATA { GRAPH <urn:test:parent> { <urn:test:s> <urn:test:level> 5 ; <urn:test:temp> 20 } }')
    return st


def _facts(st, graph):
    return {(q.subject, q.predicate, q.object) for q in quads(st, graph)}


def test_copy_then_delete_then_add(store):
    """A construct reuses the very node its retraction names, so an addition made first would
    be deleted by the retraction meant to precede it."""
    retract = ("PREFIX t: <urn:test:> DELETE { GRAPH <urn:test:child> { t:s t:level ?l } } "
               "WHERE { GRAPH <urn:test:child> { t:s t:level ?l } }")
    fork(store, "urn:test:parent", "urn:test:child", [ox.Triple(S, LEVEL, _lit(10))], [retract])
    assert _facts(store, "urn:test:child") == {(S, LEVEL, _lit(10)), (S, TEMP, _lit(20))}
    assert _facts(store, "urn:test:parent") == {(S, LEVEL, _lit(5)), (S, TEMP, _lit(20))}, \
        "the parent is untouched — a world is a value"


def test_two_retractions_spelling_one_label_two_ways_both_run(store):
    """They cannot share a head, so they run apart — the correct answer at the cost of the batch."""
    one = ("PREFIX : <urn:test:> DELETE { GRAPH <urn:test:child> { :s :level ?l } } "
           "WHERE { GRAPH <urn:test:child> { :s :level ?l } }")
    two = ("PREFIX : <urn:other:> DELETE { GRAPH <urn:test:child> { <urn:test:s> <urn:test:temp> ?t } } "
           "WHERE { GRAPH <urn:test:child> { <urn:test:s> <urn:test:temp> ?t } }")
    fork(store, "urn:test:parent", "urn:test:child", [], [one, two])
    assert _facts(store, "urn:test:child") == set(), "both deletions applied"


def test_a_retraction_that_will_not_run_retracts_nothing_and_the_fork_still_exists(store, caplog):
    with caplog.at_level("ERROR"):
        fork(store, "urn:test:parent", "urn:test:child", [ox.Triple(S, LEVEL, _lit(10))], ["DELETE nonsense"])
    assert "would not run" in caplog.text
    assert (S, LEVEL, _lit(5)) in _facts(store, "urn:test:child"), "the old reading stands, loudly"
    assert (S, LEVEL, _lit(10)) in _facts(store, "urn:test:child"), "and the adds went in"

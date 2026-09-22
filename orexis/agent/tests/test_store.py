"""Engine facts this tree writes its queries around, pinned against the ENGINE itself.

Each is a measured behaviour of pyoxigraph that no test of a READER would report: a reader
that stopped relying on one would go green, and the day the engine grows the operation
nothing would say so. AGENTS.md keeps the list; this holds the ones live queries are shaped by.
"""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from orexis.agent.store import bindings, query_over, update


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

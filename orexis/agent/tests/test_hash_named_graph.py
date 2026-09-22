"""Hashing what a named graph holds — the question a search asks at every fork.

Two worlds are the same place when they state the same facts, and a pass that cannot see a
world it has already reached spends its whole budget going nowhere. These hold the hash to
what it claims: same content, same digest, whatever the graph is called and whatever order
the triples arrived in; different content, different digest; and STABLE ACROSS PROCESSES,
which Python's own `hash` is not.
"""

from __future__ import annotations

import subprocess
import sys

import pyoxigraph as ox
import pytest

from orexis.agent.hash_named_graph import hash_named_graph
from orexis.agent.ontology import HASH
from orexis.agent.store import catalogue_of, close_catalogue, update


@pytest.fixture
def store():
    st = ox.Store()
    update(st, "INSERT DATA { GRAPH <urn:test:catalogue> { "
               "<urn:test:catalogue> a orexis:CatalogueGraph } }")
    return st


def _row(store, graph: str) -> list[str]:
    return [str(q.object.value) for q in store.quads_for_pattern(
        ox.NamedNode(graph), ox.NamedNode(HASH), None,
        ox.NamedNode(catalogue_of(store)))]


def test_one_graph_hashes_to_one_row_however_often_it_is_asked(store):
    """The hash lands on the graph's own catalogue row, and REPLACES rather than adds: a
    graph has one content, so a second hashing leaves one row and not two."""
    update(store, "INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> 1 } }")

    first = hash_named_graph(store, "urn:test:a")
    assert _row(store, "urn:test:a") == [first], "the digest is written where it is computed"

    again = hash_named_graph(store, "urn:test:a")
    assert again == first, "and asking twice about an unmoved graph answers twice the same"
    assert _row(store, "urn:test:a") == [first], "one row, not two"


def test_two_graphs_holding_the_same_facts_hash_the_same(store):
    """What the search leans on. The graphs are differently NAMED and their triples went in
    in a different order, and neither is part of where a plan stands."""
    update(store, """INSERT DATA {
      GRAPH <urn:test:a> { <urn:s> <urn:p> 1 . <urn:s> <urn:q> "two" }
      GRAPH <urn:test:b> { <urn:s> <urn:q> "two" . <urn:s> <urn:p> 1 } }""")

    assert hash_named_graph(store, "urn:test:a") == hash_named_graph(store, "urn:test:b")


def test_a_graph_that_moved_hashes_differently(store):
    """The other half, and the one that fails silently if it breaks: a search whose hash
    cannot tell two worlds apart discards the step that was making progress."""
    update(store, "INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> 1 } }")
    before = hash_named_graph(store, "urn:test:a")

    update(store, "INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> 2 } }")
    assert hash_named_graph(store, "urn:test:a") != before


def test_an_empty_graph_hashes_and_says_so(store):
    """A graph holding nothing is a state like any other — the ground before anything is
    predicted — so it has a digest rather than an error or a None."""
    assert hash_named_graph(store, "urn:test:nothing")
    assert hash_named_graph(store, "urn:test:nothing") == hash_named_graph(store, "urn:test:else")


def test_two_numbers_agreeing_to_six_decimals_are_one_place(store):
    """The old canonical form rounded, and this is that clause surviving: two worlds whose
    readings agree to six decimals were the same place before and still are."""
    update(store, "INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> 1.0000001 } }")
    update(store, "INSERT DATA { GRAPH <urn:test:b> { <urn:s> <urn:p> 1.0000002 } }")
    update(store, "INSERT DATA { GRAPH <urn:test:c> { <urn:s> <urn:p> 1.1 } }")

    assert hash_named_graph(store, "urn:test:a") == hash_named_graph(store, "urn:test:b")
    assert hash_named_graph(store, "urn:test:c") != hash_named_graph(store, "urn:test:a")


def test_the_digest_is_the_same_in_another_process():
    """WHY IT IS SHA-256 AND NOT `hash()`. Python salts `hash` per interpreter for strings, so
    a digest built on it differs between two runs of one agent — invisible inside a pass, and
    wrong the moment a hash is written down, which is what this one is. Run in a real second
    process rather than asserted about, because that is the thing that differs."""
    script = (
        "import pyoxigraph as ox;"
        "from orexis.agent.hash_named_graph import hash_named_graph;"
        "from orexis.agent.store import update;"
        "st = ox.Store();"
        "update(st, 'INSERT DATA { GRAPH <urn:test:catalogue> {"
        " <urn:test:catalogue> a orexis:CatalogueGraph } }');"
        "update(st, 'INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> \"x\" } }');"
        "print(hash_named_graph(st, 'urn:test:a'))")
    runs = {subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                           check=True, env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}
                           ).stdout.strip()
            for seed in ("1", "2")}
    assert len(runs) == 1, f"the digest moved with PYTHONHASHSEED: {runs}"

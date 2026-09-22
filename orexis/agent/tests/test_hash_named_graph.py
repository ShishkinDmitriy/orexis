"""Hashing what a named graph holds — the question a search asks at every fork.

Two worlds are the same place when they state the same facts, and a pass that cannot see a
world it has already reached spends its whole budget going nowhere.

**THE CASES SAY WHAT A GRAPH HASHES TO, AND ONE TEST SAYS WHICH ARE ALIKE.** A case is a
store; every graph it names is hashed bar the catalogue, and the diff beside it records a
digest per graph — so two graphs that are the same place say so in the same hex, where an eye
can see it. What a diff cannot do is REFUSE: regenerating one is a flag away, and two digests
that became equal by mistake would be written down as calmly as two that differ. So the
partition each case is about is declared below and asserted, and no regeneration silences it.
The two together are the claim: the diff says what, the partition says which.

What is left beside them is what a case cannot reach — a graph hashed twice, and a graph the
store has never heard of.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from orexis.agent.hash_named_graph import hash_named_graph
from orexis.agent.ontology import HASH
from orexis.agent.store import catalogue_of, graph_names, update

CASES_DIR = Path(__file__).parent / "hash_named_graph"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

#  WHICH GRAPHS OF A CASE ARE THE SAME PLACE — one set per equivalence class. Every graph a
#  case names has to stand in exactly one of them, so a case that grows a graph nobody
#  classified fails rather than going unasserted.
SAME: dict[str, list[set[str]]] = {
    "a_graph_is_its_content_and_not_its_name": [{"here", "there"}, {"elsewhere"}],
    "a_term_is_its_kind_and_not_only_its_text": [
        {"iri"}, {"text"}, {"one"}, {"number"}, {"en"}, {"de"}],
    "a_number_is_its_value_rounded": [{"integer", "decimal", "near"}, {"apart"}],
    "a_blank_node_is_its_content": [{"minted", "again"}, {"deeper"}, {"cyclic"}],
}


def _hashed(store) -> dict[str, str]:
    """Every graph of a store hashed, bar the catalogue, by the local part of its name."""
    return {g.rsplit("#", 1)[-1]: hash_named_graph(store, g)
            for g in sorted(graph_names(store)) if g != catalogue_of(store)}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_hashing_leaves_the_catalogue_the_diff_says(case, request, snapshots):
    store = snapshots.stand_in(case)
    _hashed(store)
    snapshots.held_to_diff(case, request, "hash_named_graph", snapshots.snapshot_of(store))


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_the_graphs_a_case_calls_one_place_hash_alike_and_the_rest_do_not(case, snapshots):
    """The claim each case is ABOUT, asserted rather than recorded.

    Both directions, because only one of them fails loudly. A hash that stopped telling two
    worlds apart makes a search discard the step that was making progress — no error, no empty
    result, a plan that is simply never found.
    """
    groups = SAME[case.stem]
    digests = _hashed(snapshots.stand_in(case))
    named = {g for group in groups for g in group}
    assert named <= set(digests), f"{case.stem}: {sorted(named - set(digests))} is in no graph"
    assert set(digests) - named <= {"ontology"}, \
        f"{case.stem}: {sorted(set(digests) - named - {'ontology'})} is in no group"

    for group in groups:
        one = {digests[g] for g in group}
        assert len(one) == 1, f"{case.stem}: {sorted(group)} is one place, and hashed {one}"
    apart = {sorted(group)[0]: digests[sorted(group)[0]] for group in groups}
    assert len(set(apart.values())) == len(groups), \
        f"{case.stem}: two groups hash alike — {apart}"


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 4, [c.name for c in CASES]
    assert {c.stem for c in CASES} == set(SAME), "every case declares what it calls one place"
    assert not snapshots.orphans_in(CASES_DIR)


# --- what a case cannot reach ----------------------------------------------------------------


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
    """The hash lands on the graph's own catalogue row and REPLACES rather than adds: a graph
    has one content, so a second hashing leaves one row and not two. A case hashes each of its
    graphs once, so this is what a diff beside one cannot show."""
    update(store, "INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> 1 } }")

    first = hash_named_graph(store, "urn:test:a")
    assert _row(store, "urn:test:a") == [first], "the digest is written where it is computed"

    again = hash_named_graph(store, "urn:test:a")
    assert again == first, "and asking twice about an unmoved graph answers twice the same"
    assert _row(store, "urn:test:a") == [first], "one row, not two"


def test_a_graph_the_store_never_heard_of_hashes_like_an_empty_one(store):
    """A graph holding nothing is a state like any other — the ground before anything is
    predicted — so it has a digest rather than an error or a None. No case can put one in,
    since a case's graphs are the ones it writes."""
    assert hash_named_graph(store, "urn:test:nothing")
    assert hash_named_graph(store, "urn:test:nothing") == hash_named_graph(store, "urn:test:else")

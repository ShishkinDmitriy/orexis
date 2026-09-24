"""`entail`, held to a patch of the graph it classifies into, and to what it answers.

The vocabulary defines what a reading of a property IS as classes — an intersection of the
observation class, the subject, the property and a datatype restriction on the result — and
this is the one evaluator of those definitions. A case declares the definitions genesis would
mint and the readings to classify; the diff is the types asserted, and the returned pairs are
held to the same.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from agent.entail import entail
from agent.ontology import STATE
from agent.store import Memo, graphs_of

CASES_DIR = Path(__file__).parent / "entail"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)

SENSING = "http://example.org/orexis/sensing#"
TEST = "http://example.org/test#"


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_entail_asserts_the_sides_the_patch_says(case, request, snapshots):
    store = snapshots.stand_in(case)
    (sensed,) = graphs_of(store, STATE)
    asserted = entail(store, sensed)
    snapshots.held_to_diff(case, request, "entail", snapshots.snapshot_of(store))
    said = {(n.value.rsplit("#", 1)[-1], c.value.rsplit("#", 1)[-1]) for n, c in asserted}
    assert said == {("dry", "zz.moisture.below"), ("dry", "BelowRegion"),
                    ("fine", "zz.moisture.inside"), ("fine", "InRegion"),
                    ("wet", "zz.moisture.above"), ("wet", "AboveRegion")}, said


def test_a_node_may_be_read_from_one_graph_and_classified_in_another(snapshots):
    """The sensing layer keeps a reading's key in one graph and its number in another, and
    asks for the side to be written into the first."""
    store = snapshots.stand_in(CASES[0])
    (sensed,) = graphs_of(store, STATE)
    apart = "http://example.org/test#apart"
    store.update(f"""
INSERT {{ GRAPH <{apart}> {{ ?s <http://www.w3.org/ns/sosa/hasSimpleResult> ?v }} }}
WHERE {{ GRAPH <{sensed}> {{ ?s <http://www.w3.org/ns/sosa/hasSimpleResult> ?v }} }} ;
DELETE WHERE {{ GRAPH <{sensed}> {{ ?s <http://www.w3.org/ns/sosa/hasSimpleResult> ?v }} }}""")
    assert entail(store, sensed, of=[TEST + "dry"]) == [], "the number is elsewhere, so nothing is entailed"
    asserted = entail(store, sensed, of=[TEST + "dry"], read=(sensed, apart), memo=Memo())
    assert {c.value for _, c in asserted} == {TEST + "zz.moisture.below", SENSING + "BelowRegion"}
    graph = ox.NamedNode(sensed)
    assert all(q.graph_name == graph for q in store.quads_for_pattern(ox.NamedNode(TEST + "dry"), None, None, None)
               if q.predicate.value.endswith("#type")), "classified in the graph asked, not the one read"


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert len(CASES) >= 1, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)

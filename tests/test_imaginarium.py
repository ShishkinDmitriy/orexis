"""The store a plan thinks in — what it must hold, and what must never leave it.

A rule is asked about a WORLD and not about the store, which is only possible if there is a
store in which that world is what is true. The imaginarium is it: a second pyoxigraph store, in
memory for the life of one plan, holding the graphs a rule may read and one named graph per
node of the search. See knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md.

These are about the store itself rather than about planning — what it copies, that a fork is a
fork, and that nothing crosses back. The search's own behaviour is `test_planning.py`.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent import effects
from agent.imaginarium import Imaginarium
from agent.ontology import (ONTOLOGY_GRAPH, SENSED_GRAPH, WORLD_GRAPH, beliefs_graph)

from conftest import MOISTURE, genesis_store

GARDENER = "http://example.org/orexis/world/loner#gardener"
ZZ = "http://example.org/orexis/world/loner#zz"
ACTUATE = "http://example.org/orexis#Actuate"
RESULT = "http://www.w3.org/ns/sosa/hasSimpleResult"


def _imaginarium(value=0.04):
    st = genesis_store({("zz", MOISTURE): value}, world="loner")
    return st, Imaginarium(st, beliefs_graph("gardener"), SENSED_GRAPH)


def _dose(im, sensed, litres=0.05, value=0.04):
    return effects.apply(im, ACTUATE, me=f"<{GARDENER}>", subject=f"<{ZZ}>",
                         property=f"<{MOISTURE}>", beliefs=f"<{beliefs_graph('gardener')}>",
                         sensed=f"<{sensed}>", litres=repr(litres), value=repr(value))


def test_a_rule_asked_of_the_imaginarium_answers_what_it_answers_of_the_store():
    """The whole point, and the check that would have caught the lean snapshot.

    The record budgeted for four graphs — world, derived, entailed, beliefs — on the reasoning
    that those are what the shipped rules read. Measured, that set makes this CONSTRUCT bind
    NOTHING: both the dose and the bid walk `?term market:ofGood ?good`, and a valuation term is
    stated in a package's `ontology.ttl`, so it lands in the ontology graph beside the T-Box.

    And the failure is silent — an empty result is not an error — so the only thing that catches
    it is asking the two datasets the same question and comparing the answers.
    """
    st, im = _imaginarium()

    from_store = sorted(t.object.value for t in _dose(st, SENSED_GRAPH)[0]
                        if t.predicate.value == RESULT)
    from_imaginarium = sorted(t.object.value for t in _dose(im, SENSED_GRAPH)[0]
                              if t.predicate.value == RESULT)

    assert from_store, "the rule binds against the belief base, or this test compares nothing"
    assert from_imaginarium == from_store


def test_a_node_forks_its_parents_readings_and_leaves_them_alone():
    """A world is a VALUE, written once. The search is breadth-first, so siblings are alive at
    the same time and BRANCHING is the hard case, not backtracking — a single mutable hypothesis
    graph would need save/restore around every expansion and not even a stack discipline would
    serve, because the frontier is a set rather than a path."""
    st, im = _imaginarium()
    added, retracted = _dose(im, SENSED_GRAPH)

    class _Row:                                  # what `_Node.taken` holds: means and lever
        means, via = ACTUATE, "http://example.org/orexis/world/loner#pump"

    child = im.reached(SENSED_GRAPH, (_Row(),), added, retracted)

    assert child != SENSED_GRAPH, "a node's readings are its own graph"
    assert _values_in(im, SENSED_GRAPH) == ["0.04"], "the parent is not disturbed by a child"
    assert _values_in(im, child) == sorted(t.object.value for t in added
                                           if t.predicate.value == RESULT)
    assert len(_values_in(im, child)) == 1, \
        "one reading per node, because the step retracted the one it replaces"


def test_nothing_imagined_reaches_the_store_it_was_imagined_from():
    """What makes a store of its own the right call rather than a temporary graph in the agent's:
    a graph can be forgotten to be dropped, and a store that was never on disk cannot be."""
    st, im = _imaginarium()
    before = set(st.graph_names())
    added, retracted = _dose(im, SENSED_GRAPH)

    class _Row:
        means, via = ACTUATE, "http://example.org/orexis/world/loner#pump"

    im.reached(SENSED_GRAPH, (_Row(),), added, retracted)

    assert set(st.graph_names()) == before, "a possible world escaped into the belief base"
    assert _values_in(st, SENSED_GRAPH) == ["0.04"], "the agent's readings are its own"


def test_the_snapshot_is_public_knowledge_and_the_named_private_graphs_and_nothing_else():
    """Copied and not shared, which is what makes the snapshot a snapshot: a hypothesis explored
    against a moving world is not a hypothesis. Another agent's beliefs are not named and so are
    not there — the imaginarium inherits the isolation of the store it was copied from rather
    than widening it."""
    #  A world with FOUR agents in it, because the claim is about what was left behind and a
    #  world holding one agent could not tell.
    st = genesis_store({("fern", MOISTURE): 0.30})
    im = Imaginarium(st, beliefs_graph("fern"), SENSED_GRAPH)

    assert im.public_graphs() == st.public_graphs(), \
        "public knowledge means the same thing in both, or an unqualified pattern does not"
    for graph in (ONTOLOGY_GRAPH, WORLD_GRAPH, beliefs_graph("fern"), SENSED_GRAPH):
        assert im.get_graph(graph).strip(), f"{graph} is empty in the imaginarium"
    for other in ("supplier", "tomato", "succulent"):
        assert st.get_graph(beliefs_graph(other)).strip(), f"{other} has beliefs to leave out"
        assert not im.get_graph(beliefs_graph(other)).strip(), \
            "nobody else's beliefs were asked for, so nobody else's are here"


def _values_in(store, graph: str) -> list[str]:
    """The readings sitting in one graph, as the store holds them."""
    return sorted(str(q.object.value) for q in store.quads(graph)
                  if q.predicate == ox.NamedNode(RESULT))

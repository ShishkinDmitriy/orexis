"""Every graph says what it is, on all three axes (the-mind-is-six-graphs).

The sovereign's reframe: an agent's mind is named graphs in one vocabulary, and what differs
between them is the MODALITY of what they assert. Naming that axis — beside visibility and
how-it-arrived — immediately found two misnamed joints, and these tests hold the classification
honest so the next one is found by a gate rather than by a design sitting.
"""

import pytest

from agent import genesis, loader
from agent.ontology import AG, PROVENANCE_GRAPH, beliefs_graph
from agent.store import bindings

from conftest import genesis_store

MODALITIES = {"BeliefGraph", "ConstraintGraph", "DesireGraph",
              "MenuGraph", "IntentionGraph", "HistoryGraph"}
ARRIVALS = {"Asserted", "Derived", "Entailed", "Recorded", "Received"}


def types_of(st, graph_iri: str) -> set[str]:
    """What some graph says it is, wherever it says it — the vocabulary for the static ones,
    the provenance graph for an agent's own."""
    rows = bindings(st.query_union(
        f"SELECT ?t WHERE {{ <{graph_iri}> a ?t }}"))
    return {r["t"].rsplit("#", 1)[-1] for r in rows}


def arrival_of(st, graph_iri: str) -> set[str]:
    rows = bindings(st.query_union(
        f"SELECT ?a WHERE {{ <{graph_iri}> <{AG}arrivedBy> ?a }}"))
    return {r["a"].rsplit("#", 1)[-1] for r in rows}


def test_every_public_graph_declares_a_modality_and_an_arrival():
    """The graphs the vocabulary declares. A graph that says only who may read it is a graph
    whose content a reader must guess at — which is how a region spent months being called a
    desire."""
    st = genesis_store()
    for graph in st.public_graphs():
        kinds = types_of(st, graph)
        assert kinds & MODALITIES, f"{graph} declares no modality — only {sorted(kinds)}"
        assert arrival_of(st, graph) & ARRIVALS, f"{graph} does not say how it arrived"


def test_the_region_graph_is_a_constraint():
    """The finding that named the axis: the region is the plant's operating range intersected
    with the instrument's, deduced by a rule, unmovable by the agent and refused at boot if
    violated. Whatever the capability computing it is called, that is a constraint."""
    st = genesis_store()
    kinds = types_of(st, "http://example.org/agora/graph/constraint")
    assert "ConstraintGraph" in kinds
    assert "DesireGraph" not in kinds, "the region is not anybody's want"


def test_an_agents_own_graphs_classify_themselves(tmp_path, monkeypatch):
    """A per-agent graph cannot be declared in the vocabulary — the agent does not exist until
    it does — so it says what it is at boot, into a PUBLIC classification graph.

    Public deliberately: a modality-scoped query asks `?d a ag:DesireGraph` and must resolve
    it without naming any graph instance, which is the rule that stops a query reading part of
    the truth. The static graphs have always been classified in the ontology graph, which is
    public too; the per-agent ones were going to `provenance`, which sits outside the default
    union, and a scoped query could not see them.
    """
    st = genesis_store()
    genesis.classify_own_graphs(st, "fern")
    resolved = {r["g"] for r in bindings(st.query(
        f"SELECT ?g WHERE {{ ?g a <{AG}DesireGraph> }}"))}
    assert beliefs_graph("fern") in resolved, (
        "an unscoped, instance-free query must find what this agent's graphs are")
    kinds = types_of(st, beliefs_graph("fern"))
    assert "DesireGraph" in kinds, (
        "the graph called `beliefs` holds the aim and the settings — picks, every one, and "
        "not a single belief")
    assert arrival_of(st, beliefs_graph("fern")) == {"Asserted"}


def test_the_modality_vocabulary_is_closed():
    """Six modalities and five arrivals, and the closure is the claim: everything in this
    system is said, computed one of two ways, done, or heard. A seventh modality or a sixth
    arrival is a design decision, not a term someone adds in passing."""
    st = genesis_store()
    declared = {r["m"].rsplit("#", 1)[-1] for r in bindings(st.query(
        f"SELECT ?m WHERE {{ ?m rdfs:subClassOf <{AG}Graph> }}"))}
    assert MODALITIES <= declared
    arrivals = {r["a"].rsplit("#", 1)[-1] for r in bindings(st.query(
        f"SELECT ?a WHERE {{ ?a a <{AG}Arrival> }}"))}
    assert arrivals == ARRIVALS

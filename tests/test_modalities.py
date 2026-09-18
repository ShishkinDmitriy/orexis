"""Every graph says what it is, on all three axes (the-mind-is-six-graphs).

The sovereign's reframe: an agent's mind is named graphs in one vocabulary, and what differs
between them is the MODALITY of what they assert. Naming that axis — beside visibility and
how-it-arrived — immediately found two misnamed joints, and these tests hold the classification
honest so the next one is found by a gate rather than by a design sitting.
"""

import pytest

from agent import genesis

from assembly import loader
from orexis_agent_progression.ontology import CLASSIFICATION_GRAPH, OREXIS, PROVENANCE_GRAPH, beliefs_graph
from orexis_agent_progression.store import bindings

from conftest import genesis_store

#  The desire modality's graph classes (DesireGraph, ConstraintGraph, BoundsGraph) retired
#  with #312: its carrier is a STORE, and inside a store the graphs say only who put the fact
#  there. The classes below remain graph vocabulary until their modalities' stores land.
MODALITIES = {"BeliefGraph", "MenuGraph", "IntentionGraph", "HistoryGraph"}
ARRIVALS = {"Asserted", "Derived", "Entailed", "Recorded", "Received"}


def types_of(st, graph_iri: str) -> set[str]:
    """What some graph says it is, wherever it says it — the vocabulary for the static ones,
    the provenance graph for an agent's own."""
    rows = bindings(st.query_union(
        f"SELECT ?t WHERE {{ <{graph_iri}> a ?t }}"))
    return {r["t"].rsplit("#", 1)[-1] for r in rows}


def arrival_of(st, graph_iri: str) -> set[str]:
    rows = bindings(st.query_union(
        f"SELECT ?a WHERE {{ <{graph_iri}> <{OREXIS}arrivedBy> ?a }}"))
    return {r["a"].rsplit("#", 1)[-1] for r in rows}


def test_every_public_graph_declares_a_modality_and_an_arrival():
    """The graphs the vocabulary declares. A graph that says only who may read it is a graph
    whose content a reader must guess at — which is how a region spent months being called a
    desire."""
    st = genesis_store()
    for graph in st.public_graphs():
        kinds = types_of(st, graph)
        if graph.endswith("desire/asserted"):
            #  The one public graph whose modality is a STORE (#312): the desire modality has
            #  no graph class to declare, so this one says only who put the fact there —
            #  which is the whole ruling, arrived at its first instance.
            assert arrival_of(st, graph) == {"Asserted"}
            continue
        assert kinds & MODALITIES, f"{graph} declares no modality — only {sorted(kinds)}"
        assert arrival_of(st, graph) & ARRIVALS, f"{graph} does not say how it arrived"


def test_the_regions_live_in_the_desire_modality_and_nowhere_else():
    """The finding that named the axis survives its carrier twice over: the region is deduced,
    unmovable by the agent, refused at boot if violated — and since #312 it exists only where
    the desire modality derives it. Genesis writes no constraint graph at all; a region in the
    belief base would be the home-of-record copy the record retired."""
    from conftest import desires_build

    st = genesis_store()
    assert "http://example.org/orexis/graph/constraint" not in set(st.graph_names()), \
        "genesis must derive no wants — the modality's build is the one place they come to exist"
    wants = desires_build(st, "fern")
    assert wants.query_union(
        "ASK { ?region <http://example.org/orexis#violationIs> "
        "<http://example.org/orexis#Below> }")["boolean"], \
        "and the build must hold the derived regions"


def test_an_agents_own_graphs_classify_themselves(tmp_path, monkeypatch):
    """A per-agent graph cannot be declared in the vocabulary — the agent does not exist until
    it does — so it says what it is at boot, into a PUBLIC classification graph.

    Public deliberately: a modality-scoped query asks `?d a orexis:DesireGraph` and must resolve
    it without naming any graph instance, which is the rule that stops a query reading part of
    the truth. The static graphs have always been classified in the ontology graph, which is
    public too; the per-agent ones were going to `provenance`, which sits outside the default
    union, and a scoped query could not see them.
    """
    st = genesis_store()                          # birth classified fern's pick record
    genesis.classify_kernel_graphs(st, "fern")   # and saying so again is saying it once
    resolved = {r["g"] for r in bindings(st.query(
        f"SELECT ?g WHERE {{ ?g a <{OREXIS}PickRecordGraph> }}"))}
    assert beliefs_graph("fern") in resolved, (
        "an unscoped, instance-free query must find what this agent's graphs are")
    kinds = types_of(st, beliefs_graph("fern"))
    assert "PickRecordGraph" in kinds, (
        "the graph called `beliefs` is the RECORD of picking — what birth authored and review "
        "re-picked — typed for what it IS since the modality classes retired (#312)")
    assert arrival_of(st, beliefs_graph("fern")) == {"Asserted"}


def test_the_modality_vocabulary_is_closed():
    """Six modalities and five arrivals, and the closure is the claim: everything in this
    system is said, computed one of two ways, done, or heard. A seventh modality or a sixth
    arrival is a design decision, not a term someone adds in passing."""
    st = genesis_store()
    declared = {r["m"].rsplit("#", 1)[-1] for r in bindings(st.query(
        f"SELECT ?m WHERE {{ ?m rdfs:subClassOf <{OREXIS}Graph> }}"))}
    assert MODALITIES <= declared
    arrivals = {r["a"].rsplit("#", 1)[-1] for r in bindings(st.query(
        f"SELECT ?a WHERE {{ ?a a <{OREXIS}Arrival> }}"))}
    assert arrivals == ARRIVALS


# --- a package owns its per-agent graph (#448) ------------------------------------------------

def test_the_agents_graphs_are_classified_by_their_owners_and_review_s_three_are_among_them(monkeypatch):
    """An owner classifies what it writes, when it creates it — whatever the graph is called.
    Review's three, the keeper's promises, the ledger's record: each typed by the module that
    owns it at construction, and found by `recorded_graphs()` through the classification and
    nothing about their names. Boot used to type every per-agent graph by matching names
    against a prefix each class declared; no class declares one now, and the kernel matches
    nothing."""
    from conftest import build_agent
    from orexis_capability_review.graphs import REVIEW, evidence_graph, revisions_graph, summaries_graph
    from orexis_agent_progression.ontology import PROGRESSION, promises_graph

    fern = build_agent("fern", genesis_store(), monkeypatch)
    st = fern.beliefs
    for graph, cls, ns in ((summaries_graph("fern"), "SummariesGraph", REVIEW),
                           (evidence_graph("fern"), "EvidenceGraph", REVIEW),
                           (revisions_graph("fern"), "RevisionsGraph", REVIEW),
                           (promises_graph("fern"), "PromisesGraph", PROGRESSION)):
        assert cls in types_of(st, graph) and arrival_of(st, graph) == {"Recorded"}, \
            f"{cls}: its owner classified it at construction"
        assert graph in st.graphs_of(ns + cls), "and a reader asking by class is handed it"
    #  Review's three are WORKING graphs — the agent's own and not carried — so the door that
    #  hands a reader what the agent owns hides them by design; the keeper's promises it hands.
    assert promises_graph("fern") in st.recorded_graphs()
    assert not set(st.recorded_graphs()) & {summaries_graph("fern"), evidence_graph("fern"),
                                            revisions_graph("fern")}
    assert not bindings(st.query("SELECT ?c WHERE { ?c orexis:graphPrefix ?p }")), \
        "no class declares where its graphs live — a name is for eyes, code asks the class"


def test_a_working_graph_is_the_agents_and_not_carried(monkeypatch):
    """Review's three are classified so a volume knows them from litter, and left out of what
    a plan carries and a validation reads — `orexis:WorkingGraph` says which. Classified by
    their OWNER at construction, so an agent is built to see it."""
    from conftest import build_agent
    from orexis_capability_review.graphs import evidence_graph, revisions_graph, summaries_graph
    from orexis_agent_progression.ontology import promises_graph

    fern = build_agent("fern", genesis_store(), monkeypatch)
    carried = set(fern.beliefs.recorded_graphs())
    for g in (beliefs_graph("fern"), promises_graph("fern")):
        assert g in carried
    for g in (summaries_graph("fern"), evidence_graph("fern"), revisions_graph("fern")):
        assert g not in carried, "a working graph is mine, and not that"
        assert types_of(fern.beliefs, g), "and known from litter all the same"

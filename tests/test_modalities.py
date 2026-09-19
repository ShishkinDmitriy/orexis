"""Every graph says what it is, on all three axes (the-mind-is-six-graphs).

The sovereign's reframe: an agent's mind is named graphs in one vocabulary, and what differs
between them is the MODALITY of what they assert. Naming that axis — beside visibility and
how-it-arrived — immediately found two misnamed joints, and these tests hold the classification
honest so the next one is found by a gate rather than by a design sitting.
"""

import pytest

from agent import genesis

from assembly import loader
from orexis_agent_progression.ontology import OREXIS, picks_graph
from orexis_agent_progression.store import bindings

from conftest import genesis_store
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import KNOWN

#  The desire modality's graph classes (DesireGraph, ConstraintGraph, BoundsGraph) retired
#  with #312: its carrier is a STORE, and inside a store the graphs say only who put the fact
#  there. The classes below remain graph vocabulary until their modalities' stores land.
#  `orexis:DesireGraph` is back as a CONTENT class — a graph of desire rows, beside
#  `orexis:WantGraph` — which is a different claim from the modality one #312 retired, and
#  is why neither is in this set: a graph is classified by its owner for what it holds.
MODALITIES = {"BeliefGraph", "MenuGraph", "IntentionGraph", "HistoryGraph"}
ARRIVALS = {"Asserted", "Derived", "Entailed", "Recorded", "Received"}


def types_of(st, graph_iri: str) -> set[str]:
    """What some graph says it is, wherever it says it — the catalogue, for every graph."""
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
    for graph in st.graphs_of(PUBLIC):
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
    assert wants.query(
        "ASK { ?region <http://example.org/orexis#violationIs> "
        "<http://example.org/orexis#Below> }")["boolean"], \
        "and the build must hold the derived regions"


def test_an_agents_own_graphs_classify_themselves(tmp_path, monkeypatch):
    """A per-agent graph cannot be declared in the vocabulary — the agent does not exist until
    it does — so its owner says what it is when it creates it, into the CATALOGUE, the one
    graph that says what every graph is and itself (one-catalogue-describes-every-graph-and-
    itself). Not public: a reader asks the catalogue by class through the store's door and
    never names it, and a rule reads triples and learns nothing of what a graph is.
    """
    st = genesis_store()                          # birth classified fern's pick record
    genesis.classify_kernel_graphs(st, "fern")   # and saying so again is saying it once
    assert picks_graph("fern") in st.graphs_of(OREXIS + "PickRecordGraph"), (
        "a reader asking the class, and naming no graph, must find this agent's graphs")
    kinds = types_of(st, picks_graph("fern"))
    assert "PickRecordGraph" in kinds, (
        "the graph called `beliefs` is the RECORD of picking — what birth authored and review "
        "re-picked — typed for what it IS since the modality classes retired (#312)")
    assert arrival_of(st, picks_graph("fern")) == {"Asserted"}


def test_the_modality_vocabulary_is_closed():
    """Six modalities and five arrivals, and the closure is the claim: everything in this
    system is said, computed one of two ways, done, or heard. A seventh modality or a sixth
    arrival is a design decision, not a term someone adds in passing."""
    st = genesis_store()
    declared = {r["m"].rsplit("#", 1)[-1] for r in bindings(st.query(
        f"SELECT ?m WHERE {{ ?m rdfs:subClassOf <{OREXIS}Graph> }}", st.graphs_of(PUBLIC)))}
    assert MODALITIES <= declared
    arrivals = {r["a"].rsplit("#", 1)[-1] for r in bindings(st.query(
        f"SELECT ?a WHERE {{ ?a a <{OREXIS}Arrival> }}", st.graphs_of(PUBLIC)))}
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
    #  Review's three are of no kind a rule reads — the agent's own and nobody else's business —
    #  so a reader asking for what a rule reads is handed none of them; the keeper's promises it is.
    assert promises_graph("fern") in st.graphs_of(*KNOWN)
    assert not set(st.graphs_of(*KNOWN)) & {summaries_graph("fern"), evidence_graph("fern"),
                                            revisions_graph("fern")}
    assert not bindings(st.query("SELECT ?c WHERE { ?c orexis:graphPrefix ?p }", st.graphs_of(PUBLIC))), \
        "no class declares where its graphs live — a name is for eyes, code asks the class"


def test_a_working_graph_is_the_agents_and_not_carried(monkeypatch):
    """Review's three are classified so a volume knows them from litter, and left out of what
    a plan carries and a validation reads — `orexis:WorkingGraph` says which. Classified by
    their OWNER at construction, so an agent is built to see it."""
    from conftest import build_agent
    from orexis_capability_review.graphs import evidence_graph, revisions_graph, summaries_graph
    from orexis_agent_progression.ontology import promises_graph

    fern = build_agent("fern", genesis_store(), monkeypatch)
    carried = set(fern.beliefs.graphs_of(*KNOWN))
    for g in (picks_graph("fern"), promises_graph("fern")):
        assert g in carried
    for g in (summaries_graph("fern"), evidence_graph("fern"), revisions_graph("fern")):
        assert g not in carried, "a working graph is mine, and not that"
        assert types_of(fern.beliefs, g), "and known from litter all the same"

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
    st = genesis_store()
    genesis.classify_own_graphs(st, "fern")
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

def _per_agent_classes(st) -> dict[str, tuple[str, str | None]]:
    """class -> (prefix, arrival) for every class that states where its instances live."""
    return {r["class"]: (r["prefix"], r.get("arrival")) for r in bindings(st.query(
        "SELECT ?class ?prefix ?arrival WHERE { ?class orexis:graphPrefix ?prefix . "
        "OPTIONAL { ?class orexis:arrivesBy ?arrival } }"))}


def test_every_per_agent_graph_class_says_how_its_instances_arrive():
    """Both halves or neither: a class with a prefix and no arrival is what review's three were
    for as long as the kernel listed its own, and boot now refuses it."""
    classes = _per_agent_classes(genesis_store())
    assert len(classes) >= 8, "the per-agent graph classes stopped being found"
    assert all(arrival for _, arrival in classes.values()), \
        {c for c, (_, a) in classes.items() if not a}


def test_the_agents_graphs_are_classified_by_asking_and_review_s_three_are_among_them():
    """One road for the kernel's records, the layers' ledgers and a capability's scratch: boot
    asks which classes state a prefix and an arrival and types this agent's instance of each.
    Review's three — untyped for as long as the kernel listed its own — are typed now."""
    from orexis_capability_review.graphs import evidence_graph, revisions_graph, summaries_graph

    st = genesis_store()
    genesis.classify_own_graphs(st, "fern")
    for graph, cls in ((summaries_graph("fern"), "SummariesGraph"),
                       (evidence_graph("fern"), "EvidenceGraph"),
                       (revisions_graph("fern"), "RevisionsGraph")):
        assert cls in types_of(st, graph), f"{cls} is a per-agent class and its instance is typed"
        assert arrival_of(st, graph) == {"Recorded"}
    classes = _per_agent_classes(st)
    typed = {r["g"] for r in bindings(st.query_union(
        f"SELECT ?g WHERE {{ GRAPH <{CLASSIFICATION_GRAPH}> {{ ?g a ?c }} }}"))}
    assert typed == {prefix + "fern" for prefix, _ in classes.values()}, \
        "exactly one instance per declared class, and nothing the vocabulary does not declare"


def test_a_working_graph_is_the_agents_and_not_carried():
    """Review's three are classified so a volume knows them from litter, and left out of what
    a plan carries and a validation reads — `orexis:WorkingGraph` says which."""
    from orexis_capability_review.graphs import evidence_graph, revisions_graph, summaries_graph
    from orexis_agent_progression.graphs import intentions_graph
    from orexis_agent_progression.ontology import obligations_graph, promises_graph
    from orexis_agent_deliberation.ontology import pursued_graph, remembered_graph

    st = genesis_store()
    genesis.classify_own_graphs(st, "fern")
    carried = set(st.recorded_graphs())
    for g in (beliefs_graph("fern"), intentions_graph("fern"), obligations_graph("fern"),
              promises_graph("fern"), remembered_graph("fern")):
        assert g in carried
    for g in (summaries_graph("fern"), evidence_graph("fern"), revisions_graph("fern")):
        assert g not in carried, "a working graph is mine, and not that"


def test_every_graph_builder_spells_what_its_class_declares():
    """The Python that mints a per-agent graph's name and the class that declares its prefix
    are two spellings of one fact, held together here."""
    from orexis_capability_review.graphs import evidence_graph, revisions_graph, summaries_graph
    from orexis_agent_progression.graphs import intentions_graph
    from orexis_agent_progression.ontology import obligations_graph, promises_graph, roots_graph
    from orexis_agent_deliberation.ontology import pursued_graph, remembered_graph
    from orexis_capability_sensing.terms import expectations_graph

    classes = _per_agent_classes(genesis_store())
    builders = {
        f"{OREXIS}PickRecordGraph": beliefs_graph,
        f"{OREXIS}RootsGraph": roots_graph,   # #644
        "http://example.org/orexis/market#ObligationsGraph": obligations_graph,   # the ledger's (#635)
        "http://example.org/orexis/progression#IntentionGraph": intentions_graph,
        "http://example.org/orexis/progression#PromisesGraph": promises_graph,
        "http://example.org/orexis/deliberation#RememberedGraph": remembered_graph,
        "http://example.org/orexis/deliberation#PursuedGraph": pursued_graph,
        "http://example.org/orexis/sensing#ExpectationsGraph": expectations_graph,   # #631
        "http://example.org/orexis/review#SummariesGraph": summaries_graph,
        "http://example.org/orexis/review#EvidenceGraph": evidence_graph,
        "http://example.org/orexis/review#RevisionsGraph": revisions_graph,
    }
    assert set(builders) == set(classes), "a class declared with no builder here, or the reverse"
    for cls, build in builders.items():
        assert build("x") == classes[cls][0] + "x", cls


def test_a_prefix_without_an_arrival_refuses_the_boot():
    from orexis_agent_progression.ontology import ONTOLOGY_GRAPH

    st = genesis_store()
    st.update(f"""INSERT DATA {{ GRAPH <{ONTOLOGY_GRAPH}> {{
        <urn:test#HalfGraph> a owl:Class ; rdfs:subClassOf orexis:Graph ;
            orexis:graphPrefix "http://example.org/orexis/graph/half/" }} }}""")
    with pytest.raises(RuntimeError, match="HalfGraph"):
        genesis.classify_own_graphs(st, "fern")

"""A desire is authored at genesis and never rebuilt (#644,
a-root-holds-always-and-an-outdated-graph-is-dropped).

An `orexis:Desire` is a declaration for the agent's whole life: written once at birth into
the agent's own desires graph, holding at every instant with no period, endowed on amendment, and
left untouched by every rebuild of the desire modality — which projects it beside the records
and deduces nothing.
"""
from __future__ import annotations

from agent_old import genesis
from orexis_agent_deliberation import pursuit
from orexis_agent_progression.ontology import picks_graph, desires_graph
from orexis_agent_progression.store import bindings
from conftest import build_agent, genesis_store
from orexis_agent_progression.ontology import PUBLIC

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
GARDENER = "http://example.org/orexis/world/loner#gardener"
from orexis_agent_progression.keeper import PATIENCE_S


def _roots(st, agent_id="gardener") -> set[str]:
    return {r["r"] for r in bindings(st.query(
        f"SELECT ?r WHERE {{ GRAPH <{desires_graph(agent_id)}> {{ ?me orexis:holds ?r . ?r a orexis:Desire }} }}", st.graphs_of(PUBLIC)))}


def _triples(st, agent_id="gardener") -> set[tuple]:
    return {(str(q.subject), str(q.predicate), str(q.object)) for q in st.quads(desires_graph(agent_id))
            if not str(q.subject).startswith("_:") and not str(q.object).startswith("_:")}


def _gardener(monkeypatch):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): 0.3}, world="loner")
    return st, build_agent("gardener", st, monkeypatch)


def test_the_roots_exist_after_birth_and_before_any_rebuild(monkeypatch):
    """Birth authors them, into a graph of the agent's own with no period: the region want per
    property and the freshness want per sensor, by the names the ledger has always known."""
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store(world="loner")
    desires = _roots(st)
    assert "http://example.org/orexis#desire.gardener.SoilMoisture" in desires, desires
    assert any(r.startswith("http://example.org/orexis#fresh.gardener.") for r in desires), "the freshness want is a desire too"
    assert desires_graph("gardener") not in st.periods(), "no period: it holds at every instant, as the T-Box does"


def test_a_rebuild_leaves_the_roots_untouched(monkeypatch):
    """A re-pick, an obligation, an endowment: the modality is rebuilt, and the desires graph is
    the same graph — same nodes, same triples — because the rebuild is a projection."""
    st, agent = _gardener(monkeypatch)
    before = _triples(st)
    st.update(f"""INSERT DATA {{ GRAPH <{picks_graph("gardener")}> {{ <{GARDENER}> <{PATIENCE_S}> 90 }} }}""")
    agent.desires.rebuild()
    agent.desires.rebuild()
    assert _triples(st) == before, "nothing a rebuild does reaches the desires"
    assert _roots(st) <= {r["r"] for r in bindings(agent.desires.query(
        "SELECT ?r WHERE { ?me orexis:holds ?r . ?r a orexis:Desire }"))}, \
        "and the modality projects every desire"


def test_the_rebuild_runs_no_rule(monkeypatch):
    """The packages' desire rules run at genesis and nowhere else: a rebuild that could not
    find them still builds the modality whole."""
    from assembly import loader

    st, agent = _gardener(monkeypatch)
    def refused():
        raise AssertionError("a rebuild asked for the desire rules")
    monkeypatch.setattr(loader, "desires_rule_files", refused)
    agent.desires.rebuild()
    region_want = next(d for d in agent.considering() if getattr(d, "observed_property", None) == MOISTURE and not d.is_epistemic)
    assert region_want.uri == "http://example.org/orexis#desire.gardener.SoilMoisture"


def test_a_root_the_volume_never_held_is_endowed_at_boot_and_a_held_one_stays(monkeypatch):
    """An amendment that adds a region want: the never-held desire arrives with its met-tests, and
    every desire the agent already holds is left exactly as it was — including one whose triples
    differ from what the world would derive today."""
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store(world="loner")
    desires = _roots(st)
    gone = "http://example.org/orexis#desire.gardener.SoilMoisture"
    kept = next(r for r in desires if r.startswith("http://example.org/orexis#fresh."))
    #  A volume from before the region want existed: the desire and everything hanging off it dropped.
    st.update(f"""DELETE {{ GRAPH <{desires_graph("gardener")}> {{ ?s ?p ?o }} }}
        WHERE {{ GRAPH <{desires_graph("gardener")}> {{ ?s ?p ?o .
          FILTER(?s = <{gone}> || ?o = <{gone}> || ?s = <http://example.org/orexis#bounds.gardener.SoilMoisture>
                 || ?o = <http://example.org/orexis#bounds.gardener.SoilMoisture>) }} }}""")
    #  And a held desire the agent has made its own: a label review might have rewritten.
    st.update(f"""DELETE {{ GRAPH <{desires_graph("gardener")}> {{ <{kept}> rdfs:label ?l }} }}
        INSERT {{ GRAPH <{desires_graph("gardener")}> {{ <{kept}> rdfs:label "mine now" }} }}
        WHERE {{ GRAPH <{desires_graph("gardener")}> {{ <{kept}> rdfs:label ?l }} }}""")
    assert gone not in _roots(st)
    endowed = genesis.author_roots(st, "gardener")
    assert endowed == [gone], endowed
    assert gone in _roots(st)
    assert st.query(f"ASK {{ GRAPH <{desires_graph('gardener')}> {{ <{gone}> orexis:metWhen <http://example.org/orexis#bounds.gardener.SoilMoisture> }} }}", st.graphs_of(PUBLIC))["boolean"], \
        "with its met-test"
    labels = bindings(st.query(f"SELECT ?l WHERE {{ GRAPH <{desires_graph('gardener')}> {{ <{kept}> rdfs:label ?l }} }}", st.graphs_of(PUBLIC)))
    assert [r["l"] for r in labels] == ["mine now"], "a held desire stays the agent's, whatever the world would say"
    assert genesis.author_roots(st, "gardener") == [], "and endowment is idempotent"

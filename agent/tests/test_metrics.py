"""The metrics a pass writes: selects each package ships in a graph of a kind of their own, found by
that kind, run over the store each names and summed across its stores — and a select that fails
costing the agent nothing. What each package's figures ARE on a real pass is held by the worlds'
own tests, hanoi's and the greenhouse's."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox

from agent import clock
from agent.metrics import METRIC_GRAPH, declared, measure, measurement_of
from agent.ontology import BELIEF, PUBLIC
from agent.runtime import BELIEF_BASE, IMAGINARIUM, INTENTIONS_STORE, PASS, Runtime, boot, world_of
from agent.store import close_catalogue, closed, document, graphs_of, put_document

AGENT = Path(__file__).resolve().parents[1]
ROOT = AGENT.parent
HANOI = ROOT / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
SHIPPED = sorted(AGENT.rglob("metrics.ttl"))


def _every_package():
    """The metrics of every package, as the operator's tools read a world: every package loaded."""
    return world_of(HANOI)


def test_every_package_that_counts_ships_its_metrics_as_their_own_kind():
    """Planning, execution, sensing and belief each ship a `metrics.ttl`, and each says it is a
    metric graph — the kind, and not the file's name, is what the metrics module reads."""
    assert {p.parent.name for p in SHIPPED} >= {"planning", "execution", "sensing", "belief"}, SHIPPED
    store = _every_package()
    held = set(graphs_of(store, METRIC_GRAPH))
    assert {p.resolve().as_uri() for p in SHIPPED} == held


def test_the_kind_is_neither_public_nor_a_belief():
    """Beneath `orexis:Graph` and nothing else, so no reader of public knowledge or of beliefs is
    ever handed a select, and no possible world is filled with one."""
    store = _every_package()
    assert set(closed(store, METRIC_GRAPH)) == {METRIC_GRAPH, "http://example.org/orexis#Graph"}
    metric = set(graphs_of(store, METRIC_GRAPH))
    assert metric and not metric & set(graphs_of(store, PUBLIC, BELIEF))


def test_no_select_crosses_into_a_possible_world(monkeypatch):
    """After a pass that forks worlds, no imaginarium holds a quad of any metric graph: the
    catalogue crosses, and says what the graph is, but its selects stay in the belief base."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(HANOI, "hanoi"), "hanoi", budget=20)
    runtime.run(passes=1, poll_s=0)
    metric = graphs_of(runtime.beliefs, METRIC_GRAPH)
    assert metric and all(any(runtime.beliefs.quads_for_pattern(None, None, None, ox.NamedNode(g))) for g in metric)
    assert runtime.planner.imaginaria, "the pass imagined nothing — the guard would compare nothing"
    for im in runtime.planner.imaginaria.values():
        crossed = [g for g in metric if any(im.quads_for_pattern(None, None, None, ox.NamedNode(g)))]
        assert not crossed, f"a possible world's store holds {crossed}"


def test_a_metric_is_named_once_and_never_as_the_runtimes_own():
    """A point is measured under its metric's local name, so two metrics of one name would write
    one measurement with two meanings, and one named like the runtime's would share its fields."""
    names = [measurement_of(m["metric"]) for m in declared(_every_package())]
    assert names and len(names) == len(set(names)), names
    assert PASS not in names


def test_no_list_of_metrics_exists():
    """What the metrics are is the packages' documents' to say: neither the module that runs them nor
    the runtime that hands it the stores names one."""
    names = {measurement_of(m["metric"]) for m in declared(_every_package())}
    assert names, "no metric is declared — the guard would look for nothing"
    for path in (AGENT / "metrics.py", AGENT / "runtime.py"):
        spelled = {n.value for n in ast.walk(ast.parse(path.read_text()))
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)} & names
        assert not spelled, f"{path.name} names the metrics {sorted(spelled)}"


def _with(tmp_path: Path, beliefs: ox.Store, text: str) -> ox.Store:
    """`beliefs`, holding one more metric graph, written for the case."""
    path = tmp_path / "metrics.ttl"
    path.write_text("@prefix orexis: <http://example.org/orexis#> .\n@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                    "@prefix execution: <http://example.org/orexis/execution#> .\n"
                    "<> a orexis:MetricGraph .\n" + text)
    put_document(beliefs, document(path))
    close_catalogue(beliefs)
    return beliefs


def test_a_select_is_run_over_every_store_of_its_repository_and_summed(tmp_path):
    """A count over two stores of one repository is the two counts added — the imaginaria are one
    per scope — and a store of another repository is not asked."""
    beliefs = _with(tmp_path, boot(HANOI, "hanoi"), """<#graphs> a orexis:Metric ; orexis:over execution:IntentionsStore ;
        sh:select "SELECT (COUNT(DISTINCT ?g) AS ?graphs) WHERE { GRAPH ?g { ?s ?p ?o } }" .\n""")
    one, two = ox.Store(), ox.Store()
    one.add(ox.Quad(ox.NamedNode("urn:s"), ox.NamedNode("urn:p"), ox.NamedNode("urn:o"), ox.NamedNode("urn:g1")))
    two.add(ox.Quad(ox.NamedNode("urn:s"), ox.NamedNode("urn:p"), ox.NamedNode("urn:o"), ox.NamedNode("urn:g2")))
    two.add(ox.Quad(ox.NamedNode("urn:s"), ox.NamedNode("urn:p"), ox.NamedNode("urn:o"), ox.NamedNode("urn:g3")))
    (point,) = [p for p in measure(beliefs, {INTENTIONS_STORE: [one, two], BELIEF_BASE: [beliefs]}, NOW)
                if p["measurement"] == "graphs"]
    assert point["fields"] == {"graphs": 3} and isinstance(point["fields"]["graphs"], int)
    assert point["time"] == NOW
    assert "graphs" not in {p["measurement"] for p in measure(beliefs, {BELIEF_BASE: [beliefs]}, NOW)}, \
        "a repository with no store handed has no point"


def test_a_select_that_fails_costs_the_agent_nothing(tmp_path, caplog):
    """A select the engine refuses, and one reading the catalogue of a store that has none, are
    said in the log; every other metric is written."""
    beliefs = _with(tmp_path, boot(HANOI, "hanoi"), """
<#broken> a orexis:Metric ; orexis:over orexis:BeliefBase ; sh:select "SELECT nothing at all" .
<#catalogued> a orexis:Metric ; orexis:over execution:IntentionsStore ;
    sh:select "SELECT (COUNT(?g) AS ?n) WHERE { GRAPH $cat { ?g a orexis:Graph } }" .\n""")
    written = {p["measurement"] for p in measure(beliefs, {BELIEF_BASE: [beliefs], IMAGINARIUM: [],
                                                           INTENTIONS_STORE: [ox.Store()]}, NOW)}
    assert "broken" not in written and "catalogued" not in written
    assert {"revisions", "intentions"} <= written, written
    assert "broken could not be read" in caplog.text and "catalogued could not be read" in caplog.text

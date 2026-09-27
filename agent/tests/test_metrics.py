"""The metrics a pass writes: selects each package ships in a graph of a kind of their own, found by
that kind, run over the store each names and summed across its stores — and a select that fails
costing the agent nothing. What each package's figures ARE on a real pass is held by the worlds'
own tests, hanoi's and the greenhouse's."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox

from agent import clock, metrics
from agent.metrics import METRIC_GRAPH, begin, declared, events, measure, measurement_of
from agent.ontology import BELIEF, PUBLIC
from agent.runtime import (BELIEF_BASE, IMAGINARIUM, INTENTIONS_STORE, PASS, PHASES, UNREACHABLE, Runtime, boot,
                           world_of)
from agent.series import METRICS, Sink, install
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


def test_a_metric_or_an_event_is_named_once_and_never_as_the_runtimes_own():
    """A point is measured under its metric's or its event's local name, so two of one name would
    write one measurement with two meanings, and one named like the runtime's would share its fields."""
    store = _every_package()
    names = [measurement_of(m["metric"]) for m in declared(store)] + list(events(store))
    assert names and len(names) == len(set(names)), names
    assert not {PASS, PHASES, UNREACHABLE} & set(names)


def test_every_event_the_tree_writes_is_declared_by_a_package():
    """An event is written by the code that does the work and declared, with the fields it carries,
    in its package's metric graph — which is what the dashboards draw. Held over every `metrics.event`
    the tree calls: its measurement is declared, or it is the runtime's own; and every figure a
    declaration names is one the code writes, since a declared field nobody writes is a panel of
    nothing."""
    declared_events = events(_every_package())
    called = {}
    for path in sorted(AGENT.rglob("*.py")):
        if "tests" in path.parts:
            continue
        for n in ast.walk(ast.parse(path.read_text())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "event" \
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "metrics":
                called.setdefault(n.args[0].value if isinstance(n.args[0], ast.Constant) else n.args[0].id,
                                  set()).add(path.relative_to(ROOT).as_posix())
    assert len(called) >= 7, f"the scan found {sorted(called)} — the pattern stopped matching"
    assert set(called) - {"UNREACHABLE"} == set(declared_events), called
    source = "\n".join(p.read_text() for p in AGENT.rglob("*.py") if "tests" not in p.parts)
    written = lambda f: f'"{f}"' in source or (f.endswith("_s") and f'lap("{f[:-2]}")' in source)   # a lap writes `<part>_s`
    unwritten = {(e, f) for e, fields in declared_events.items() for f in fields if not written(f)}
    assert not unwritten, f"declared and written by nothing: {sorted(unwritten)}"


def test_an_event_is_stamped_from_the_pass_and_reads_no_clock(monkeypatch):
    """Stamped at the pass's instant moved on by real seconds, so two events of one pass are two
    points, and the agent's clock — which a test ticks per read — is never read."""
    def read():
        raise AssertionError("an event read the agent's clock")
    written = []
    install(METRICS, Sink(METRICS, "m", lambda bucket, record: written.extend(record)))
    try:
        begin(NOW)
        monkeypatch.setattr(clock, "now", read)
        metrics.event("search", {"duration_s": 0.1})
        metrics.event("search", {"duration_s": 0.2})
    finally:
        install(METRICS, None)
    first, second = (p["time"] for p in written)
    assert NOW <= first < second < NOW + timedelta(seconds=1)


def test_a_timing_never_reads_the_agents_clock(monkeypatch):
    """COMPUTE TIME IS `perf_counter`. The same hanoi run, with a metrics sink and without, on a clock
    that ticks per read as the allotment's does: the clock is read as often either way and the tower
    is solved the same, so no timing, stamp or event read the agent's timeline — where one had, the
    counts differ, and on a ticking clock the run itself would too."""
    def run(sink_loaded: bool) -> tuple[int, int, str]:
        reads = [0]
        def tick():
            reads[0] += 1
            return NOW + timedelta(seconds=reads[0])
        monkeypatch.setattr(clock, "now", tick)
        written = []
        if sink_loaded:
            install(METRICS, Sink(METRICS, "m", lambda bucket, record: written.extend(record)))
        try:
            outcome = Runtime(boot(HANOI, "hanoi"), "hanoi", budget=20).run(passes=12, poll_s=0)
        finally:
            install(METRICS, None)
        return reads[0], len(written), outcome
    without, with_ = run(False), run(True)
    assert with_[1] > 0 and without[1] == 0, "the sink was loaded for one run and not the other"
    assert (with_[0], with_[2]) == (without[0], without[2]), f"clock reads {with_[0]} with a sink, {without[0]} without"


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

"""The kernel of the metrics: an event tallied in memory and written once a window, a gauge sampled
at the flush over the stores it is handed, every point at the flush's real instant — and nothing
read, timed or written where no metrics sink is loaded. What each package's figures ARE on a real
run is held by the worlds' own tests, hanoi's, the greenhouse's and the terrace's."""

from __future__ import annotations

import importlib
import logging
import signal
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock, metrics, runtime as runtime_module
from agent.metrics import Event, Gauge, counted, declared, due, flush, sample
from agent.runtime import EVERY, Runtime, boot
from agent.series import METRICS, Sink, install

AGENT = Path(__file__).resolve().parents[1]
HANOI = AGENT.parent / "world" / "hanoi"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
WALL = datetime(2030, 6, 1, 8, 0, tzinfo=timezone.utc)

TRIED = Event("tried", values=("duration_s", "weighed"), flags=("gave_up",), tags=("outcome",))


class Monotonic:
    """A real clock a test moves by hand."""

    def __init__(self):
        self.at = 1000.0

    def __call__(self) -> float:
        return self.at


@pytest.fixture(autouse=True)
def fresh():
    metrics.reset()
    yield
    install(METRICS, None)
    metrics.reset()
    metrics.identify()


@pytest.fixture
def written():
    out = []
    install(METRICS, Sink(METRICS, "m", lambda bucket, record: out.extend(record)))
    return out


def test_an_event_is_tallied_and_written_once_a_window(written):
    """Nothing is written as it happens. At the end of the window a point per measurement and tag
    set: how many, each value's sum, mean and max, and each flag's count — nought where none was
    raised, so the field is there to divide by — every point at the flush's instant on the wall,
    tagged with who speaks."""
    real = Monotonic()
    metrics.configure(interval_s=60, monotonic=real, wall=lambda: WALL)
    metrics.identify(world="hanoi", agent="mover")
    TRIED({"duration_s": 0.5, "weighed": 20, "gave_up": True}, outcome="Exhausted")
    TRIED({"duration_s": 1.5, "weighed": 20, "gave_up": False}, outcome="Exhausted")
    TRIED({"duration_s": 0.25, "weighed": 7}, outcome="Satisfied")
    real.at += 59
    assert not due() and written == [], "a window is sixty seconds, and nothing is written inside one"
    real.at += 1
    assert due()
    points = {p["tags"]["outcome"]: p for p in flush()}
    assert points["Exhausted"]["fields"] == {"count": 2, "gave_up": 1, "duration_s_sum": 2.0, "duration_s_mean": 1.0,
                                             "duration_s_max": 1.5, "weighed_sum": 40.0, "weighed_mean": 20.0,
                                             "weighed_max": 20.0}
    assert points["Satisfied"]["fields"]["gave_up"] == 0 and points["Satisfied"]["fields"]["count"] == 1
    assert all(p["time"] == WALL and p["measurement"] == "tried" for p in points.values())
    assert all(p["tags"] == {"world": "hanoi", "agent": "mover", "outcome": o} for o, p in points.items())
    assert len(written) == 2
    assert not due() and flush() == [], "the next window opened empty"


def test_every_aggregate_of_a_value_is_a_float_so_no_window_changes_a_fields_type(written):
    """Influx refuses a field whose type changes, so a value's three are floats whatever it was
    handed, and a count and a flag are integers."""
    TRIED({"weighed": 3})
    (point,) = flush()
    assert all(isinstance(v, float) for k, v in point["fields"].items() if k.startswith("weighed_"))
    assert isinstance(point["fields"]["count"], int) and isinstance(point["fields"]["gave_up"], int)


def test_a_field_or_tag_not_declared_is_left_out_and_said_once(written, caplog):
    """A want's name on a point would be a tag of unbounded values or a field nothing aggregates, so
    an event carries what it declares and nothing else — and a mistake is said in the log, once."""
    with caplog.at_level(logging.WARNING, logger="metrics"):
        TRIED({"weighed": 1, "want": "every_disk_home"}, outcome="Satisfied", want="every_disk_home")
        TRIED({"weighed": 1, "want": "every_disk_home"}, outcome="Satisfied", want="every_disk_home")
    (point,) = flush()
    assert "every_disk_home" not in {*point["fields"], *map(str, point["fields"].values()), *point["tags"].values()}
    assert caplog.text.count("carries want") == 1 and caplog.text.count("tagged want") == 1


def test_with_no_sink_nothing_is_tallied_and_a_new_sink_starts_an_empty_window(written):
    """Where no sink is loaded an event is nothing; a sink installed in place of another opens a
    window of its own, so no tally crosses from one to the other."""
    TRIED({"weighed": 1})
    install(METRICS, None)
    TRIED({"weighed": 2})
    assert not metrics.recording() and not due() and flush() == []
    other = []
    install(METRICS, Sink(METRICS, "m2", lambda bucket, record: other.extend(record)))
    TRIED({"weighed": 3})
    (point,) = flush()
    assert point["fields"]["weighed_sum"] == 3.0 and point["fields"]["count"] == 1
    assert written == [] and other == [point]


def test_the_window_is_the_environments_or_sixty_seconds():
    assert metrics.load({}) == 60.0
    assert metrics.load({"METRICS_INTERVAL_S": "15"}) == 15.0
    assert metrics.load({"METRICS_INTERVAL_S": "never"}) == 60.0
    assert metrics.load({"METRICS_INTERVAL_S": "0"}) == 60.0, "a window of nothing is a test's, never a deployment's"


def test_a_select_gauge_is_summed_across_the_stores_it_is_handed():
    """A count over two stores is the two counts added — the imaginaria are one per scope — and an
    integer stays one."""
    one, two = ox.Store(), ox.Store()
    for store, graphs in ((one, ["urn:g1"]), (two, ["urn:g2", "urn:g3"])):
        for g in graphs:
            store.add(ox.Quad(ox.NamedNode("urn:s"), ox.NamedNode("urn:p"), ox.NamedNode("urn:o"), ox.NamedNode(g)))
    found = counted([one, two], "SELECT (COUNT(DISTINCT ?g) AS ?graphs) WHERE { GRAPH ?g { ?s ?p ?o } }")
    assert found == {"graphs": 3} and isinstance(found["graphs"], int)


def test_a_gauge_that_fails_costs_the_agent_nothing(monkeypatch, caplog):
    """A select the engine refuses, and one reading the catalogue of a store that has none, are said
    in the log; every other gauge of the module is sampled."""
    module = types.ModuleType("a_package_metrics")
    module.BROKEN = Gauge("broken", "SELECT nothing at all")
    module.CATALOGUED = Gauge("catalogued", "SELECT (COUNT(?g) AS ?n) WHERE { GRAPH $cat { ?g a orexis:Graph } }")
    module.FINE = Gauge("fine", read=lambda stores: {"stores": len(stores)})
    monkeypatch.setitem(sys.modules, module.__name__, module)
    with caplog.at_level(logging.WARNING, logger="metrics"):
        sampled = {g.name: fields for g, fields in sample(module.__name__, [ox.Store()])}
    assert sampled == {"fine": {"stores": 1}}
    assert "broken could not be read" in caplog.text and "catalogued could not be read" in caplog.text


def _every_module() -> dict[str, types.ModuleType]:
    """The runtime's module and every package's `metrics.py`, by the package — what the dashboards
    import. Importing sensing's here is a test's, not a boot's."""
    out = {"runtime": runtime_module}
    for package in EVERY:
        if (AGENT / package / "metrics.py").exists():
            out[package] = importlib.import_module("agent." + package.replace("/", ".") + ".metrics")
    return out


def test_every_package_that_reports_keeps_it_in_one_module_and_every_name_is_its_own():
    """Planning, execution, sensing and belief each keep a `metrics.py`, and no measurement is named
    twice across them and the runtime — two of one name would be one measurement with two meanings."""
    modules = _every_module()
    assert {"planning", "execution", "sensing", "belief"} <= set(modules), sorted(modules)
    names = [m.name for module in modules.values() for m in declared(module.__name__)]
    assert len(names) >= 15 and len(names) == len(set(names)), names
    assert not list(AGENT.rglob("metrics.ttl")), "a metric is code, and no document declares one"


def test_a_flush_reads_no_agent_clock(monkeypatch, written):
    """Stamped by the wall at the flush — never by the agent's timeline, which a test ticks per read."""
    def read():
        raise AssertionError("a metric read the agent's clock")
    monkeypatch.setattr(clock, "now", read)
    TRIED({"weighed": 1})
    before = datetime.now(timezone.utc)
    (point,) = flush()
    assert before <= point["time"] <= datetime.now(timezone.utc)


def test_a_timing_never_reads_the_agents_clock(monkeypatch):
    """COMPUTE TIME IS `perf_counter` AND THE WINDOW IS REAL. The same hanoi run, with a metrics sink
    flushing every pass and without one, on a clock that ticks per read as the allotment's does: the
    clock is read as often either way and the tower is solved the same, so no timing, tally or flush
    read the agent's timeline — where one had, the counts differ, and on a ticking clock the run
    itself would too."""
    def run(sink_loaded: bool) -> tuple[int, int, str]:
        reads = [0]
        def tick():
            reads[0] += 1
            return NOW + timedelta(seconds=reads[0])
        monkeypatch.setattr(clock, "now", tick)
        written = []
        if sink_loaded:
            install(METRICS, Sink(METRICS, "m", lambda bucket, record: written.extend(record)))
            metrics.configure(interval_s=0)
        try:
            outcome = Runtime(boot(HANOI, "hanoi"), "hanoi", budget=20).run(passes=12, poll_s=0)
        finally:
            install(METRICS, None)
        return reads[0], len(written), outcome
    without, with_ = run(False), run(True)
    assert with_[1] > 0 and without[1] == 0, "the sink was loaded for one run and not the other"
    assert (with_[0], with_[2]) == (without[0], without[2]), f"clock reads {with_[0]} with a sink, {without[0]} without"


def test_the_last_window_is_written_as_the_process_stops(monkeypatch):
    """A stop is an exit: SIGTERM raises, and whatever ends the run, `main` writes the window it was
    in — the pass tallied, every gauge sampled once — rather than losing up to a minute of it."""
    written = []
    monkeypatch.setattr(runtime_module.series, "load",
                        lambda: install(METRICS, Sink(METRICS, "m", lambda bucket, record: written.extend(record))) or (METRICS,))
    monkeypatch.setattr(clock, "now", lambda: NOW)
    before = signal.getsignal(signal.SIGTERM)
    ran = Runtime.run

    def stopped(self, **kwargs):
        ran(self, passes=1, poll_s=0)
        raise SystemExit(128 + signal.SIGTERM)                   # what the handler raises
    monkeypatch.setattr(Runtime, "run", stopped)
    try:
        with pytest.raises(SystemExit):
            runtime_module.main([str(HANOI), "hanoi"])
        assert signal.getsignal(signal.SIGTERM) is runtime_module._stopped
    finally:
        signal.signal(signal.SIGTERM, before)
    by = {p["measurement"]: p for p in written}
    assert by["pass"]["fields"]["count"] == 1, "the one pass, tallied and written at the stop"
    assert {"store", "process", "plans", "cone", "intentions", "acts", "revisions"} <= set(by), sorted(by)
    assert {p["tags"]["world"] for p in written} == {"hanoi"}

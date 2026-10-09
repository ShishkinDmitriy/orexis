"""The window: an event tallied in memory by what its class marks and written once a window, a level
written as it last stood, every point at the flush's real instant — and nothing tallied or written
where no metrics sink is loaded. What each package's figures ARE on a real run is held by the worlds'
own tests, hanoi's for a planner alone, the courier's for a plan walked, the greenhouse's and the
terrace's."""

from __future__ import annotations

import importlib
import signal
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock, runtime as runtime_module
from agent.metrics import Flag, Level, Tag, Value, measurement, reported
from agent.metrics import window as metrics
from agent.metrics.window import due, flush
from agent.runtime import Runtime, boot, every_package
from agent.series import METRICS, Sink, install

AGENT = Path(__file__).resolve().parents[2]
COURIER = AGENT.parent / "world" / "courier"
TOWER = AGENT.parent / "world" / "tower"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
WALL = datetime(2030, 6, 1, 8, 0, tzinfo=timezone.utc)

@dataclass(frozen=True)
class Tried:
    metric = "tried"
    want: str = "every_disk_home"
    outcome: Tag = None
    duration_s: Value = None
    weighed: Value = None
    gave_up: Flag = False


@dataclass(frozen=True)
class Held:
    metric = "held"
    scope: Tag = None
    worlds: Level = None


def TRIED(fields: dict, **tags) -> None:
    metrics.tally(Tried(**fields, **tags))


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


def test_a_field_the_class_does_not_mark_is_not_written(written):
    """A want's name on a point would be a tag of unbounded values or a field nothing aggregates, so
    an event's unmarked fields are the event's and not the metric's."""
    metrics.tally(Tried(want="every_disk_home", outcome="Satisfied", weighed=1))
    (point,) = flush()
    assert "every_disk_home" not in {*point["fields"], *map(str, point["fields"].values()), *point["tags"].values()}
    assert "want" not in point["tags"]


def test_a_level_is_written_as_it_last_stood_and_only_in_a_window_that_said_it(written):
    """Two reports in a window: the last is written, per tag set, and no count beside it; the next
    window, in which nobody said it, writes none."""
    metrics.tally(Held(scope="hanoi", worlds=20))
    metrics.tally(Held(scope="hanoi", worlds=7))
    metrics.tally(Held(scope="courier", worlds=3))
    points = {p["tags"]["scope"]: p for p in flush()}
    assert points["hanoi"]["fields"] == {"worlds": 7.0} and points["courier"]["fields"] == {"worlds": 3.0}
    assert flush() == []


def test_a_level_keeps_the_type_it_was_said_in(written):
    """A count said as an integer is written as one, and a measure as a float: the series store
    refuses a field whose type changes, and the gauges before wrote their counts as integers, so a
    count written as a float had every point of its measurement refused (#856, measured live)."""
    metrics.tally(Held(scope="hanoi", worlds=20))
    metrics.tally(Held(scope="courier", worlds=2.5))
    points = {p["tags"]["scope"]: p["fields"]["worlds"] for p in flush()}
    assert points == {"hanoi": 20, "courier": 2.5}
    assert isinstance(points["hanoi"], int) and isinstance(points["courier"], float)


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


def _every_module() -> dict:
    """The runtime's module and every package's `events.py`, by the package — what the dashboards
    import. Importing sensing's here is a test's, not a boot's."""
    out = {"runtime": runtime_module}
    for package in every_package():
        if (AGENT / package / "events.py").exists():
            out[package] = importlib.import_module("agent." + package.replace("/", ".") + ".events")
    return out


def test_every_package_that_reports_keeps_it_on_its_events_and_every_name_is_its_own():
    """Planning, execution, sensing and belief each keep an `events.py`, and no measurement is named
    twice across them and the runtime — two of one name would be one measurement with two meanings."""
    modules = _every_module()
    assert {"planning", "execution", "sensing", "belief"} <= set(modules), sorted(modules)
    names = [measurement(cls) for module in modules.values() for cls in reported(module)]
    assert len(names) >= 15 and len(names) == len(set(names)), names
    assert not list(AGENT.rglob("metrics.ttl")), "a metric is code, and no document declares one"
    assert not [p for p in AGENT.rglob("metrics.py")], "a package reports by its events, and keeps no metrics module"


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
    """COMPUTE TIME IS `perf_counter` AND THE WINDOW IS REAL. The same courier run, with a metrics sink
    flushing every pass and without one, on a clock that ticks per read as the allotment's does: the
    clock is read as often either way and the run ends the same, so no timing, tally or flush read
    the agent's timeline — where one had, the counts differ, and on a ticking clock the run itself
    would too. The courier's, and no longer Hanoi's, since a planner that is no executor walks
    nothing (#928): in twelve passes the plan is found, adopted and its first steps taken, so the
    executor's tallies — the act, the landing, the intentions standing — are in it beside the
    planner's."""
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
            outcome = Runtime(boot(COURIER, "courier"), "courier", budget=128).run(passes=12, poll_s=0)
        finally:
            install(METRICS, None)
        return reads[0], len(written), outcome, {p["measurement"] for p in written}
    without, with_ = run(False), run(True)
    assert with_[1] > 0 and without[1] == 0, "the sink was loaded for one run and not the other"
    assert {"search", "published", "intentions", "act", "landing"} <= with_[3], sorted(with_[3])
    assert (with_[0], with_[2]) == (without[0], without[2]), f"clock reads {with_[0]} with a sink, {without[0]} without"


def test_the_last_window_is_written_as_the_process_stops(monkeypatch):
    """A stop is an exit: SIGTERM raises, and whatever ends the run, `main` stops every part and the
    metrics part writes the window it was in — the pass tallied, every level as it last stood — rather
    than losing up to a minute of it. The tower's mover, which plans, walks and deliberates, so the
    window holds every one of those three packages' figures."""
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
            runtime_module.main([str(TOWER), "mover"])
        assert signal.getsignal(signal.SIGTERM) is runtime_module._stopped
    finally:
        signal.signal(signal.SIGTERM, before)
    by = {p["measurement"]: p for p in written}
    assert by["pass"]["fields"]["count"] == 1, "the one pass, tallied and written at the stop"
    assert by["pass"]["fields"]["quads"] > 0 and by["pass"]["fields"]["uptime_s"] > 0
    assert {"planner", "imaginarium", "search", "revise", "revisions", "intentions"} <= set(by), sorted(by)
    assert {p["tags"]["world"] for p in written} == {"tower"}

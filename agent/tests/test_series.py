"""The series sink: loaded for a purpose where the environment names a store for it, writing what it
is handed and knowing nothing of what that is — and a refusal said in the log, never raised. What a
point IS is the contributing package's, held by sensing's and execution's own tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from agent.series import HISTORY, METRICS, PURPOSES, Sink, install, load, sink

AGENT = Path(__file__).resolve().parents[1]
NAMED = {"INFLUX_HISTORY_URL": "http://localhost:8086", "INFLUX_HISTORY_ORG": "orexis",
         "INFLUX_HISTORY_BUCKET": "terrace-terrace", "INFLUX_HISTORY_TOKEN": "t"}
METRICS_NAMED = {"INFLUX_METRICS_URL": "http://localhost:8086", "INFLUX_METRICS_ORG": "orexis",
                 "INFLUX_METRICS_BUCKET": "terrace-terrace-metrics", "INFLUX_METRICS_TOKEN": "m"}


@pytest.fixture(autouse=True)
def _no_sink_outlives_a_test():
    yield
    for purpose in PURPOSES:
        install(purpose, None)


def test_a_sink_writes_what_it_is_handed_to_its_bucket():
    written = []
    point = {"measurement": "anything", "tags": {}, "fields": {"x": 1.0}}
    assert Sink(HISTORY, "b", lambda bucket, record: written.append((bucket, record))).write([point]) == 1
    assert written == [("b", [point])]


def test_nothing_handed_is_nothing_written():
    written = []
    assert Sink(HISTORY, "b", lambda bucket, record: written.append(record)).write([]) == 0
    assert written == []


def test_a_store_that_refuses_costs_the_agent_nothing(caplog):
    def refuse(bucket, record):
        raise ConnectionError("down")
    assert Sink(HISTORY, "b", refuse).write([{"measurement": "m", "fields": {"x": 1}}]) == 0
    assert "refused" in caplog.text


def test_no_store_named_for_a_purpose_is_no_sink():
    assert Sink.from_environment(HISTORY, {}) is None
    assert load({}) == () and sink(HISTORY) is None


def test_a_store_named_without_a_purpose_is_no_sink():
    """The environment 0.2.0 used to hand an agent named one bucket with no purpose to it; a store
    is named for a purpose now, and the old keys name nothing."""
    assert load({"INFLUX_URL": "http://localhost:8086", "INFLUX_ORG": "orexis",
                 "INFLUX_BUCKET": "terrace-terrace", "INFLUX_TOKEN": "t"}) == ()


def test_a_store_half_named_is_no_sink_and_says_what_is_missing(caplog):
    half = {k: v for k, v in NAMED.items() if k != "INFLUX_HISTORY_TOKEN"}
    assert Sink.from_environment(HISTORY, half) is None
    assert "INFLUX_HISTORY_TOKEN" in caplog.text


def test_a_store_named_for_history_is_the_history_sink():
    assert load(NAMED) == (HISTORY,)
    assert sink(HISTORY).bucket == "terrace-terrace" and sink(METRICS) is None
    install(HISTORY, None)
    assert sink(HISTORY) is None


def test_each_purpose_is_told_its_own_store_and_one_names_nothing_of_the_other():
    """Metrics are named under their own keys, to a bucket of their own; the one environment holding
    both loads both, and holding metrics alone loads no history."""
    assert load(METRICS_NAMED) == (METRICS,)
    assert sink(METRICS).bucket == "terrace-terrace-metrics" and sink(HISTORY) is None
    assert load({**NAMED, **METRICS_NAMED}) == (HISTORY, METRICS)
    assert (sink(HISTORY).bucket, sink(METRICS).bucket) == ("terrace-terrace", "terrace-terrace-metrics")


def test_the_sink_imports_nothing_of_the_agent():
    """Beneath every contributor: it may be imported by sensing and execution, and imports none of
    them — nor anything of `agent`, since a point is the client's own dict, handed through."""
    tree = ast.parse((AGENT / "series.py").read_text())
    reaching = [n.lineno for n in ast.walk(tree)
                if (isinstance(n, ast.ImportFrom) and (n.module or "").startswith("agent"))
                or (isinstance(n, ast.Import) and any(a.name.startswith("agent") for a in n.names))]
    assert not reaching, f"agent/series.py imports the agent at lines {reaching}"


def test_the_runtime_loads_the_sinks_and_writes_metrics_and_never_history():
    """What history holds is decided by the packages that decide each thing, so the runtime never
    names it; what it asks of the sink module is to `load`, and the metrics sink, which it writes
    at the end of a pass."""
    tree = ast.parse((AGENT / "runtime.py").read_text())
    said = {n.attr for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "series"}
    assert said == {"load", "sink", "METRICS"}, f"the runtime asks the sink module for {sorted(said)}"
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "agent.series"
             for a in n.names}
    assert not names, f"the runtime imports {sorted(names)} from the sink"
    assert PURPOSES == (HISTORY, METRICS), "a new purpose is a new case here"

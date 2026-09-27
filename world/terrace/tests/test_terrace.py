"""The terrace on Agent 0.2.0: the sentinel's one message is four observations, the soil's side is
concluded against the bed's range, and the agent — holding no desire — watches and sends nothing,
and keeps running, since a transport reaches it."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.ontology import OREXIS, STATE
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import graphs_of, rows
from agent.series import HISTORY, Sink, install
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT = "http://example.org/orexis/world/terrace#terrace_agent"
MESSAGE = json.dumps({"moisture": 0.2, "temperature": 14.5, "humidity": 0.8, "pressure": 1012}).encode()


class Broker:
    def __init__(self):
        self.subscribed, self.published = [], []

    def subscribe(self, pattern):
        self.subscribed.append(pattern)

    def publish(self, topic, payload, retain=False):
        self.published.append(topic)


@pytest.fixture
def history():
    """The history sink the environment would name, as `orexis-compose terrace` names it: what the
    packages contribute, in the order they did."""
    written = []
    install(HISTORY, Sink(HISTORY, "terrace-terrace", lambda bucket, record: written.extend(record)))
    yield written
    install(HISTORY, None)


def _terrace(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    broker = Broker()
    return Runtime(boot(WORLD, "terrace"), "terrace", transport=Mqtt(AGENT, broker)), broker


def test_booted_from_its_directory_the_agent_holds_no_hardware():
    """The hardware is onboarding's kind, which the agent's T-Box does not declare, so a boot from
    the world's directory passes over it: not one of its quads, and no row saying it exists. A
    container used to be spared only because the file was left unmounted by its name (#820)."""
    store = boot(WORLD, "terrace")
    hardware = (WORLD / "hardware.ttl").resolve().as_uri()
    held = sum(1 for _ in store.quads_for_pattern(None, None, None, ox.NamedNode(hardware)))
    rowed = sum(1 for _ in store.quads_for_pattern(ox.NamedNode(hardware), None, None))
    assert (held, rowed) == (0, 0), f"the terrace agent holds {held} hardware quads and {rowed} rows about the graph"


def test_the_agent_listens_on_the_boards_one_topic(monkeypatch):
    _, broker = _terrace(monkeypatch)
    assert broker.subscribed == ["sensors/moisture_sensor_terrace/reading"]


def test_one_message_is_four_observations_and_the_soil_is_below_the_beds_range(monkeypatch):
    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    assert runtime.run(passes=2, poll_s=0) == UNFINISHED, "it watches for good"
    read = {r["p"].rsplit("#", 1)[-1]: float(r["v"]) for r in rows(
        runtime.beliefs, "SELECT ?p ?v WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v }",
        graphs_of(runtime.beliefs, STATE))}
    assert read == {"SoilMoisture": 0.2, "AirTemperature": 14.5, "AirHumidity": 0.8, "AirPressure": 1012.0}
    below = rows(runtime.beliefs, "SELECT DISTINCT ?o WHERE { ?o sensing:below ?r }", graphs_of(runtime.beliefs, OREXIS + "BeliefGraph"))
    assert [r["o"].rsplit("#", 1)[-1] for r in below] == ["obs_terrace_bed_SoilMoisture"]
    assert broker.published == [], "nothing is wanted, so nothing is sent"


def test_each_reading_reaches_the_series_under_its_own_property(monkeypatch, history):
    """The four values of one message are four points, each measured under the property it
    observes — the air's temperature is not soil moisture (#822) — and contributed by sensing as
    it writes each observation (#825)."""
    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    runtime.sense(NOW)
    assert sorted((p["measurement"], p["tags"]["sensor"], p["fields"]["value"]) for p in history) == [
        ("AirHumidity", "air_humidity_terrace", 0.8), ("AirPressure", "air_pressure_terrace", 1012.0),
        ("AirTemperature", "air_temp_terrace", 14.5), ("SoilMoisture", "moisture_sensor_terrace", 0.2)]
    assert {p["tags"]["plant"] for p in history} == {"terrace_bed"}
    assert {p["time"] for p in history} == {NOW}, "at the reading's own instant"


def test_every_point_the_agent_writes_is_drawn_by_one_terrace_panel(monkeypatch, history):
    """What `orexis-dashboards terrace` generates is held to what the agent writes: each point's
    measurement and sensor are filtered for by exactly one panel, so a panel querying a
    measurement nobody writes, which is what an unshared constant would drift into, fails here."""
    from onboarding.dashboards import render

    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    runtime.sense(NOW)
    queries = [t["query"] for panel in render("terrace")["panels"] for t in panel["targets"]]
    drawn = {(p["measurement"], p["tags"]["sensor"]):
             [q for q in queries if f'r._measurement == "{p["measurement"]}"' in q
              and f'r.sensor == "{p["tags"]["sensor"]}"' in q] for p in history}
    assert len(drawn) == 4 and all(len(panels) == 1 for panels in drawn.values()), drawn


def test_every_field_the_agent_writes_is_drawn_by_one_health_panel(monkeypatch):
    """The health dashboard is held to what two passes write, flushed as a stop flushes (#826,
    amended): every field of every point is drawn by exactly one panel — a gauge whole, an event's
    count and flags together and each value's mean, max and sum together — and every panel reads the
    bucket of the agent the dashboard's variable picks. A row per package that reports, the runtime's
    first: sensing's because the terrace loads it, so its silence and its readings are drawn, and no
    panel draws a measurement nothing writes."""
    from agent import metrics
    from agent.series import METRICS
    from onboarding.dashboards import AGENT_VARIABLE, render_health

    written = []
    install(METRICS, Sink(METRICS, "terrace-terrace-metrics", lambda bucket, record: written.extend(record)))
    try:
        runtime, _ = _terrace(monkeypatch)
        for _ in range(2):
            runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
            runtime.run(passes=1, poll_s=0)
        runtime.report()
    finally:
        install(METRICS, None)
        metrics.reset()
    health = render_health("terrace")
    (variable,) = health["templating"]["list"]
    assert variable["name"] == AGENT_VARIABLE and variable["query"] == "terrace"
    rows_ = [p["title"] for p in health["panels"] if p["type"] == "row"]
    assert rows_[0] == "runtime" and {"planning", "execution", "sensing", "belief"} <= set(rows_[1:]), rows_
    panels = [p for p in health["panels"] if p["type"] != "row"]
    queries = [[t["query"] for t in p["targets"]] for p in panels]
    assert queries and all('from(bucket: "terrace-${agent}-metrics")' in q for qs in queries for q in qs)
    wanted = {(p["measurement"], f) for p in written for f in p["fields"]}
    assert {("silence", "silent"), ("received", "interval_s_mean"), ("reroot", "count"), ("pass", "plan_s_max")} <= wanted, wanted
    for measurement, field in wanted:
        hits = [i for i, qs in enumerate(queries) if any(
            f'r._measurement == "{measurement}"' in q and (f'r._field == "{field}"' in q or "r._field ==" not in q)
            for q in qs)]
        assert len(hits) == 1, (measurement, field, [panels[i]["title"] for i in hits])
    drawn = {q.split('r._measurement == "')[1].split('"')[0] for qs in queries for q in qs}
    assert {p["measurement"] for p in written} <= drawn

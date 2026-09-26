"""The terrace on Agent 0.2.0: the sentinel's one message is four observations, the soil's side is
concluded against the bed's range, and the agent — holding no desire — watches and sends nothing,
and keeps running, since a transport reaches it."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent import clock
from agent.ontology import OREXIS, STATE
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import graphs_of, rows
from agent.series import Series
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


def _terrace(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    broker = Broker()
    series = Series("terrace-terrace", lambda bucket, record: broker.points.extend(record))
    broker.points = []
    return Runtime(boot(WORLD, "terrace"), "terrace", transport=Mqtt(AGENT, broker), series=series), broker


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


def test_each_reading_reaches_the_series_as_the_terrace_panels_draw_it(monkeypatch):
    """The Grafana terrace folder filters on the `sensor` tag of `soil_moisture`; the four values of
    one message are four points, tagged as the 0.1.0 agent tagged them."""
    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    runtime.sense(NOW)
    assert sorted((p["tags"]["sensor"], p["fields"]["value"]) for p in broker.points) == [
        ("air_humidity_terrace", 0.8), ("air_pressure_terrace", 1012.0),
        ("air_temp_terrace", 14.5), ("moisture_sensor_terrace", 0.2)]
    assert {p["measurement"] for p in broker.points} == {"soil_moisture"}
    assert {p["tags"]["plant"] for p in broker.points} == {"terrace_bed"}

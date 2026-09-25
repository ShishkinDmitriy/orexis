"""The greenhouse in the 0.2.0 runtime: readings arrive over MQTT, sensing writes them and the rules
conclude their sides, the grower's desire mints a want where a side is below, the plan's step is
taken by sending the device a command sized from the reading, and the next reading answers it.
The broker is a fake client: what is subscribed to and published is what is held."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import OREXIS
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import graphs_of, rows
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"


class Broker:
    """What the grower subscribes to and publishes, and nothing else of MQTT."""

    def __init__(self):
        self.subscribed, self.published = [], []

    def subscribe(self, pattern):
        self.subscribed.append(pattern)

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, json.loads(payload), retain))


class Clock:
    """One timeline for the world and the agent: a test sets where it stands, and every read
    after that moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


def _grower(monkeypatch):
    time = Clock(NOW)
    monkeypatch.setattr(clock, "now", time)
    beliefs = boot(WORLD, "grower")
    broker = Broker()
    runtime = Runtime(beliefs, "grower", transport=Mqtt(GH + "grower", broker))
    runtime.time = time
    return runtime, broker


def _sides(beliefs) -> set[tuple[str, str]]:
    q = """SELECT ?p ?side WHERE { ?obs sosa:observedProperty ?p ; ?side ?range .
           VALUES ?side { sensing:below sensing:inside sensing:above } }"""
    return {(r["p"].rsplit("#", 1)[-1], r["side"].rsplit("#", 1)[-1])
            for r in rows(beliefs, q, graphs_of(beliefs, OREXIS + "BeliefGraph"))}


def test_the_grower_listens_to_the_instruments_of_the_bed_it_acts_for(monkeypatch):
    _, broker = _grower(monkeypatch)
    assert sorted(broker.subscribed) == ["sensors/moisture_probe/reading", "sensors/thermometer/reading"]


def test_a_reading_is_written_and_its_side_concluded(monkeypatch):
    runtime, _ = _grower(monkeypatch)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    runtime.sense(NOW)
    assert ("SoilMoisture", "below") in _sides(runtime.beliefs), "under the bed's floor of 0.30"


def test_a_dry_bed_is_dosed_by_a_command_sized_from_the_reading_and_the_next_reading_answers_it(monkeypatch):
    """0.2 against a range of 0.30 to 0.60: the middle is 0.45, two litres a fraction make half a
    litre, which is the pump's cap. The dose goes out on the pump's topic, not retained; the next
    reading, 0.45, is revised inside and the intention is done."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.2}', NOW)
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED
    assert broker.published == [("actuators/pump/command", {"dose_ml": 500}, False)]
    assert len(runtime.executor.walking()) == 1, "the world has not answered yet"
    runtime.time.at = NOW + timedelta(minutes=5)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', runtime.time.at)
    runtime.run(passes=2, poll_s=0)
    assert runtime.executor.walking() == [], "the reading was revised inside and answered the dose"
    assert ("SoilMoisture", "inside") in _sides(runtime.beliefs)
    assert len(broker.published) == 1, "one dose, and nothing more once the bed is comfortable"


def test_a_cold_bed_is_heated_for_as_long_as_the_gap_takes(monkeypatch):
    """16 degrees against 18 to 24: the middle is 21, five degrees at two an hour is two and a half
    hours, and the heater runs at most an hour a command."""
    runtime, broker = _grower(monkeypatch)
    runtime.deliver("sensors/moisture_probe/reading", b'{"value": 0.45}', NOW)
    runtime.deliver("sensors/thermometer/reading", b'{"value": 16.0}', NOW)
    runtime.run(passes=1, poll_s=0)
    assert broker.published == [("actuators/heater/command", {"heat_s": 3600}, False)]

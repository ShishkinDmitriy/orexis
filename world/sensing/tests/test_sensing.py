"""The sensing world on Agent 0.2.0: the governed board's one message is three observations, the
agent watches and keeps running, and a cadence it would set goes to the board's own command topic."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox

from agent import clock
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import graphs_of, rows
from agent.transport.mqtt.driver import Mqtt

OBSERVATION_GRAPH = "http://example.org/orexis/sensing#ObservationGraph"      # sensing's, where a percept is kept

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
W = "http://example.org/orexis/world/sensing#"
MESSAGE = json.dumps({"moisture": 0.41, "temperature": 21.5, "humidity": 0.55}).encode()


class Broker:
    def __init__(self):
        self.subscribed, self.published = [], []

    def subscribe(self, pattern):
        self.subscribed.append(pattern)

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, json.loads(payload), retain))


def _fern(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    broker = Broker()
    return Runtime(boot(WORLD, "fern"), "fern", transport=Mqtt(W + "fern_agent", broker)), broker


def test_booted_from_its_directory_the_agent_holds_no_hardware():
    """The hardware is onboarding's kind and not the agent's, so the boot passes over it (#820)."""
    store = boot(WORLD, "fern")
    hardware = (WORLD / "hardware.ttl").resolve().as_uri()
    held = sum(1 for _ in store.quads_for_pattern(None, None, None, ox.NamedNode(hardware)))
    rowed = sum(1 for _ in store.quads_for_pattern(ox.NamedNode(hardware), None, None))
    assert (held, rowed) == (0, 0), f"the fern agent holds {held} hardware quads and {rowed} rows about the graph"


def test_one_message_is_three_observations_and_the_agent_watches(monkeypatch):
    runtime, broker = _fern(monkeypatch)
    assert broker.subscribed == ["sensors/moisture_sensor_fern/reading"]
    runtime.deliver("sensors/moisture_sensor_fern/reading", MESSAGE, NOW)
    assert runtime.run(passes=2, poll_s=0) == UNFINISHED
    read = {r["p"].rsplit("#", 1)[-1]: float(r["v"]) for r in rows(      # the numbers, and what the rules concluded of them
        runtime.beliefs, "SELECT ?p ?v WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v }",
        graphs_of(runtime.beliefs, OBSERVATION_GRAPH))}               # a percept, and its revision of its kind too (#944)
    assert read == {"SoilMoisture": 0.41, "AirTemperature": 21.5, "AirHumidity": 0.55}
    assert broker.published == []


def test_a_cadence_goes_to_the_boards_own_command_topic_retained(monkeypatch):
    """The governed board keeps the interval it was last told, retained on the broker."""
    runtime, broker = _fern(monkeypatch)
    assert runtime.transport.set_cadence(runtime.beliefs, W + "moisture_sensor_fern", 10) is True
    assert broker.published == [("sensors/moisture_sensor_fern/command", {"sleep_s": 10}, True)]

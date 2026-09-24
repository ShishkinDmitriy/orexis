"""`Link` over a stand-in client with paho's shape: it subscribes what the world implies, a
message the client delivers becomes observations, and a command the driver hands it is published."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agent import clock
from agent.transport.mqtt.link import Link
from agent.store import rows

WORLD = Path(__file__).parent / "worlds" / "a_board_on_a_bus.trig"
TEST = "http://example.org/test#"


@dataclass
class Message:
    topic: str
    payload: bytes


@dataclass
class Client:
    """What paho's client looks like to the link: subscribe, publish, and an on_message it sets."""
    subscribed: list = field(default_factory=list)
    published: list = field(default_factory=list)
    on_message: object = None

    def subscribe(self, pattern: str) -> None:
        self.subscribed.append(pattern)

    def publish(self, topic: str, payload: bytes, retain: bool = False) -> None:
        self.published.append((topic, payload, retain))

    def deliver(self, topic: str, payload: bytes) -> None:
        self.on_message(self, None, Message(topic, payload))


def test_the_link_listens_where_the_agents_sensors_publish(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store, client = snapshots.stand_in(WORLD), Client()
    assert Link(store, snapshots.ME, client).open() == ["sensors/board/reading"]
    assert client.subscribed == ["sensors/board/reading"], "the lamp's topic is the neighbour's, and the probe has none"


def test_a_delivered_message_is_received_at_the_present(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store, client = snapshots.stand_in(WORLD), Client()
    Link(store, snapshots.ME, client).open()
    client.deliver("sensors/board/reading", b'{"temperature": 21.5, "humidity": 0.61}')
    taken = rows(store, "SELECT ?t WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:resultTime ?t } }", ())
    assert len(taken) == 2 and all(r["t"].startswith("2026-01-01T12:00:00") for r in taken)


def test_a_command_from_the_driver_leaves_as_the_firmwares_document(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store, client = snapshots.stand_in(WORLD), Client()
    link = Link(store, snapshots.ME, client)
    assert link.driver.set_cadence(store, TEST + "thermo", 120) is True
    assert client.published == [("sensors/board/command", json.dumps({"sleep_s": 120}).encode(), True)]

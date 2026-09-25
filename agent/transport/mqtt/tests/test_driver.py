"""The MQTT driver over a board on a bus and a stand-in client with paho's shape: what a sensor
claims, what the agent subscribes to, whose a message is, where a command goes and as what, how
a message becomes observations through sensing — and MQTT's own filter matching."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agent import clock
from agent.transport.mqtt.driver import Mqtt, matches
from agent.store import rows

WORLD = Path(__file__).parent / "worlds" / "a_board_on_a_bus.trig"
TEST = "http://example.org/test#"
THERMO, HYGRO, PROBE, PHOTOMETER = (TEST + n for n in ("thermo", "hygro", "probe", "photometer"))
OBSERVED = "http://example.org/orexis/graph/observed/keeper/"
BOARD_MESSAGE = b'{"temperature": 21.5, "humidity": 0.61}'

_RESULTS_Q = "SELECT ?p ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v } } ORDER BY ?p"


@dataclass
class Client:
    """What paho's client looks like to the driver: subscribe and publish."""
    subscribed: list = field(default_factory=list)
    published: list = field(default_factory=list)

    def subscribe(self, pattern: str) -> None:
        self.subscribed.append(pattern)

    def publish(self, topic: str, payload: bytes, retain: bool = False) -> None:
        self.published.append((topic, payload, retain))


@pytest.fixture
def bus(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    client = Client()
    return snapshots.stand_in(WORLD), Mqtt(snapshots.ME, client), client


def _results(store):
    return [(r["p"].rsplit("#", 1)[-1], float(r["v"])) for r in rows(store, _RESULTS_Q, ())]


def test_a_sensor_that_publishes_on_a_topic_speaks_mqtt_and_one_that_does_not_does_not(bus):
    store, _, _ = bus
    assert Mqtt.claims(store, THERMO) and Mqtt.claims(store, PHOTOMETER)
    assert not Mqtt.claims(store, PROBE), "the probe is in the pot and on no bus"


def test_the_subscription_is_the_pattern_of_the_filter_naming_the_topic(bus):
    store, driver, _ = bus
    assert driver.subscriptions(store, THERMO) == ["sensors/board/reading"]
    assert driver.subscriptions(store, HYGRO) == ["sensors/board/reading"], "one board, one topic, two sensors"
    assert driver.subscriptions(store, PHOTOMETER) == ["sensors/lamp/+"]
    assert driver.subscriptions(store, PROBE) == []


def test_a_message_is_the_sensors_when_its_pattern_matches_the_channel(bus):
    store, driver, _ = bus
    assert driver.owns(store, THERMO, "sensors/board/reading")
    assert not driver.owns(store, THERMO, "sensors/lamp/reading")
    assert driver.owns(store, PHOTOMETER, "sensors/lamp/reading") and driver.owns(store, PHOTOMETER, "sensors/lamp/status")
    assert not driver.owns(store, PHOTOMETER, "sensors/lamp/reading/raw")


def test_the_driver_listens_where_the_agents_sensors_publish(bus):
    store, driver, client = bus
    assert driver.open(store) == ["sensors/board/reading"]
    assert client.subscribed == ["sensors/board/reading"], "the lamp's topic is the neighbour's, and the probe has none"


def test_a_command_goes_to_the_topic_the_board_listens_on_as_the_firmwares_document(bus):
    store, driver, client = bus
    assert driver.set_cadence(store, THERMO, 60) is True
    driver.sense_now(store, HYGRO)
    assert client.published == [("sensors/board/command", json.dumps({"sleep_s": 60}).encode(), True),
                                ("sensors/board/command", json.dumps({"sense": True}).encode(), False)]


def test_a_sensor_whose_board_listens_nowhere_takes_no_command(bus, caplog):
    store, driver, client = bus
    with caplog.at_level("WARNING", logger="mqtt"):
        assert driver.set_cadence(store, PHOTOMETER, 60) is False
        driver.sense_now(store, PROBE)
    assert client.published == [] and "listens on no topic" in caplog.text


def test_one_message_on_the_boards_topic_is_two_observations(bus, snapshots):
    store, driver, _ = bus
    written = driver.handle(store, "sensors/board/reading", BOARD_MESSAGE, snapshots.NOW)
    assert written == [(HYGRO, OBSERVED + "zamioculcas_humidity"), (THERMO, OBSERVED + "zamioculcas_warmth")]
    assert _results(store) == [("humidity", 0.61), ("warmth", 21.5)]
    taken = rows(store, "SELECT ?t WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:resultTime ?t } }", ())
    assert len(taken) == 2 and all(r["t"].startswith("2026-01-01T12:00:00") for r in taken)


def test_a_neighbours_message_on_the_same_broker_is_not_received(bus, snapshots):
    """The lamp's photometer publishes for a fern the keeper does not act for: the broker may
    deliver it, and it is nobody's of the keeper's."""
    store, driver, _ = bus
    assert driver.handle(store, "sensors/lamp/reading", b'{"value": 300}', snapshots.NOW) == []
    assert driver.handle(store, "sensors/nowhere", BOARD_MESSAGE, snapshots.NOW) == []
    assert _results(store) == []


def test_a_message_a_sensor_cannot_read_writes_nothing_for_it(bus, snapshots, caplog):
    store, driver, _ = bus
    with caplog.at_level("WARNING", logger="pipeline"):
        written = driver.handle(store, "sensors/board/reading", b'{"temperature": 21.5}', snapshots.NOW)
    assert written == [(THERMO, OBSERVED + "zamioculcas_warmth")], "the hygrometer's field is missing, the thermometer's is there"
    assert "unread" in caplog.text


def test_filter_matching_is_mqtts_own():
    assert matches("sensors/board/reading", "sensors/board/reading")
    assert matches("sensors/+/reading", "sensors/board/reading") and not matches("sensors/+/reading", "sensors/a/b/reading")
    assert matches("sensors/#", "sensors/board/reading") and matches("sensors/#", "sensors")
    assert matches("#", "anything/at/all") and not matches("#", "$SYS/broker/load")
    assert not matches("sensors/#/reading", "sensors/board/reading"), "# ends a filter or matches nothing"
    assert not matches("sensors/board", "sensors/board/reading")

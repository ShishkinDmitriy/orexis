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
from agent.transport.transport import Transport
from agent.store import rows

WORLD = Path(__file__).parent / "worlds" / "a_board_on_a_bus.trig"
TEST = "http://example.org/test#"
THERMO, HYGRO, PROBE, PHOTOMETER = (TEST + n for n in ("thermo", "hygro", "probe", "photometer"))
OBSERVED = "http://example.org/orexis/graph/observed/keeper/"
BOARD_MESSAGE = b'{"temperature": 21.5, "humidity": 0.61}'

_RESULTS_Q = "SELECT ?p ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v } } ORDER BY ?p"


@dataclass
class Message:
    topic: str
    payload: bytes


@dataclass
class Client:
    """What paho's client looks like to the driver: subscribe and publish, and for `connect`
    the two setters, the connection and the loop, with an `on_message` it sets."""
    subscribed: list = field(default_factory=list)
    published: list = field(default_factory=list)
    tls: tuple | None = None
    credential: tuple | None = None
    connected: tuple | None = None
    looping: bool = False
    on_message: object = None

    def subscribe(self, pattern: str) -> None:
        self.subscribed.append(pattern)

    def publish(self, topic: str, payload: bytes, retain: bool = False) -> None:
        self.published.append((topic, payload, retain))

    def tls_set(self, ca_certs=None, certfile=None, keyfile=None) -> None:
        self.tls = (ca_certs, certfile, keyfile)

    def username_pw_set(self, username, password=None) -> None:
        self.credential = (username, password)

    def connect(self, host, port) -> None:
        self.connected = (host, port)

    def loop_start(self) -> None:
        self.looping = True


BY_PASSWORD = {"MQTT_HOST": "broker", "MQTT_PORT": "1888", "MQTT_USERNAME": "keeper", "MQTT_PASSWORD": "s3cret"}


@pytest.fixture
def bus(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    client = Client()
    return snapshots.stand_in(WORLD), Mqtt(snapshots.ME, client), client


def _results(store):
    return [(r["p"].rsplit("#", 1)[-1], float(r["v"])) for r in rows(store, _RESULTS_Q, ())]


def test_a_sensor_that_publishes_on_a_topic_speaks_mqtt_and_one_that_does_not_does_not(bus):
    store, driver, _ = bus
    assert isinstance(driver, Transport), "the family's contract, answered"
    assert Mqtt.claims(store, THERMO) and Mqtt.claims(store, PHOTOMETER)
    assert not Mqtt.claims(store, PROBE), "the probe is in the pot and on no bus"


def test_the_driver_listens_where_the_agents_sensors_publish(bus):
    store, driver, client = bus
    assert driver.open(store) == ["sensors/board/reading"], "one board, one topic, two sensors"
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


def test_connect_brings_the_bus_up_from_the_environment_and_delivers_to_the_container(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    delivered, session = [], Client()
    bus = Mqtt.connect(snapshots.ME, lambda topic, payload, at: delivered.append((topic, payload, at)), environ=BY_PASSWORD, client=session)
    assert isinstance(bus, Mqtt) and bus.client is session
    assert session.credential == ("keeper", "s3cret") and session.connected == ("broker", 1888) and session.looping
    assert session.tls is None, "no certificate in the environment, so by password"
    session.on_message(session, None, Message("sensors/board/reading", b"{}"))
    assert delivered == [("sensors/board/reading", b"{}", snapshots.NOW)], "to the container's queue, at the present"


def test_connect_uses_a_certificate_and_the_tls_port_where_the_environment_holds_one(snapshots):
    session = Client()
    Mqtt.connect(snapshots.ME, lambda *a: None, client=session,
                 environ={**BY_PASSWORD, "MQTT_CA": "ca.pem", "MQTT_CERT": "keeper.pem", "MQTT_KEY": "keeper.key", "MQTT_TLS_PORT": "8888"})
    assert session.tls == ("ca.pem", "keeper.pem", "keeper.key") and session.connected == ("broker", 8888)


def test_connect_refuses_to_guess_a_host_or_a_credential(snapshots):
    with pytest.raises(RuntimeError, match="MQTT_HOST"):
        Mqtt.connect(snapshots.ME, lambda *a: None, environ={"MQTT_USERNAME": "keeper"}, client=Client())
    with pytest.raises(RuntimeError, match="MQTT_USERNAME"):
        Mqtt.connect(snapshots.ME, lambda *a: None, environ={"MQTT_HOST": "broker"}, client=Client())


def test_filter_matching_is_mqtts_own():
    assert matches("sensors/board/reading", "sensors/board/reading")
    assert matches("sensors/+/reading", "sensors/board/reading") and not matches("sensors/+/reading", "sensors/a/b/reading")
    assert matches("sensors/#", "sensors/board/reading") and matches("sensors/#", "sensors")
    assert matches("#", "anything/at/all") and not matches("#", "$SYS/broker/load")
    assert not matches("sensors/#/reading", "sensors/board/reading"), "# ends a filter or matches nothing"
    assert not matches("sensors/board", "sensors/board/reading")

"""The MQTT driver over a board on a bus: what a sensor claims, what the agent subscribes to for
it, whose a message is, where a command goes — and MQTT's own filter matching."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.transport.mqtt.driver import Mqtt, matches

WORLD = Path(__file__).parent / "worlds" / "a_board_on_a_bus.trig"
TEST = "http://example.org/test#"
THERMO, HYGRO, PROBE, PHOTOMETER = (TEST + n for n in ("thermo", "hygro", "probe", "photometer"))


@pytest.fixture
def bus(snapshots):
    sent = []
    return snapshots.stand_in(WORLD), Mqtt(lambda topic, payload, retain: sent.append((topic, payload, retain))), sent


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


def test_a_command_goes_to_the_topic_the_board_listens_on(bus):
    store, driver, sent = bus
    assert driver.set_cadence(store, THERMO, 60) is True
    driver.sense_now(store, HYGRO)
    assert sent == [("sensors/board/command", {"sleep_s": 60}, True), ("sensors/board/command", {"sense": True}, False)]


def test_a_sensor_whose_board_listens_nowhere_takes_no_command(bus, caplog):
    store, driver, sent = bus
    with caplog.at_level("WARNING", logger="mqtt"):
        assert driver.set_cadence(store, PHOTOMETER, 60) is False
        driver.sense_now(store, PROBE)
    assert sent == [] and "listens on no topic" in caplog.text


def test_filter_matching_is_mqtts_own():
    assert matches("sensors/board/reading", "sensors/board/reading")
    assert matches("sensors/+/reading", "sensors/board/reading") and not matches("sensors/+/reading", "sensors/a/b/reading")
    assert matches("sensors/#", "sensors/board/reading") and matches("sensors/#", "sensors")
    assert matches("#", "anything/at/all") and not matches("#", "$SYS/broker/load")
    assert not matches("sensors/#/reading", "sensors/board/reading"), "# ends a filter or matches nothing"
    assert not matches("sensors/board", "sensors/board/reading")

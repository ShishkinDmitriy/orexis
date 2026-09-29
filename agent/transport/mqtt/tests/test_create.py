"""The MQTT transport's part: brought up from the environment, then started — subscribed, attached,
asking after its sensors' missing readings every minute — and stopped."""

from __future__ import annotations

from pathlib import Path

from agent.transport.mqtt import create as creating
from agent.transport.mqtt.driver import NUDGE_S, Mqtt

from .test_driver import WORLD, Client


def test_its_part_listens_is_attached_and_asks_after_missing_readings(monkeypatch, snapshots, stand_in_runtime):
    client = Client()
    monkeypatch.setattr(Mqtt, "connect", classmethod(lambda cls, me, deliver=None, **kw: cls(me, client)))
    runtime = stand_in_runtime(snapshots.stand_in(WORLD), snapshots.ME, snapshots.NOW)
    member = creating.create(runtime)
    member.start(runtime)
    assert runtime.attached == [member] and member in runtime.held
    assert client.subscribed == ["sensors/board/reading"]
    assert [seconds for seconds, _ in runtime.timers] == [NUDGE_S]

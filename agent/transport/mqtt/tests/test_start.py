"""The MQTT transport's `start`: brought up from the environment, started — subscribed, attached,
asking after its sensors' missing readings every minute — and its stop answered."""

from __future__ import annotations

from pathlib import Path

from agent.transport.mqtt import start as starting
from agent.transport.mqtt.driver import NUDGE_S, Mqtt

from .test_driver import WORLD, Client


def test_started_it_listens_is_attached_and_asks_after_missing_readings(monkeypatch, snapshots, stand_in_runtime):
    client = Client()
    monkeypatch.setattr(Mqtt, "connect", classmethod(lambda cls, me, deliver=None, **kw: cls(me, client)))
    runtime = stand_in_runtime(snapshots.stand_in(WORLD), snapshots.ME, snapshots.NOW)
    stop = starting.start(runtime)
    [member] = runtime.attached
    assert client.subscribed == ["sensors/board/reading"]
    assert [seconds for seconds, _ in runtime.timers] == [NUDGE_S]
    assert stop == member.stop

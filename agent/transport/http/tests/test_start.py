"""The HTTP transport's `start`: brought up, started — attached, and polling each of its sensors at
once and then every frequency the sensor states."""

from __future__ import annotations

from agent import clock
from agent.transport.http import start as starting
from agent.transport.http.driver import Http

from .test_driver import BODY, WEATHER, WORLD


def test_started_it_polls_each_sensor_at_its_frequency(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    asked = []
    monkeypatch.setattr(Http, "connect", classmethod(
        lambda cls, me, deliver=None, **kw: cls(me, None, lambda url: asked.append(url) or BODY, spawn=lambda work: work())))
    runtime = stand_in_runtime(snapshots.stand_in(WORLD), snapshots.ME, snapshots.NOW)
    starting.start(runtime)
    [member] = runtime.attached
    [(seconds, poll)] = runtime.timers
    assert seconds == 3600.0, "the weather service states sixty minutes"
    assert poll() == [] and len(asked) == 1
    [job] = runtime.jobs
    assert [g.rsplit("/", 1)[-1] for g in job()] == ["weather_20260101T120000Z", "weather_20260101T130000Z"]

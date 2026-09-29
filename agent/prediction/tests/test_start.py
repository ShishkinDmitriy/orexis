"""Prediction's `start`: once started it answers every observation a job writes — a graph of the
kernel's state kind holding a node a sensor made — by rewriting that sensor's predictions, and a
graph holding no sensor's node, a silence or a peer's word, by nothing."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.ontology import STATE
from agent.prediction.start import start
from agent.sensing.received import received

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
PROBE = "http://example.org/test#probe"


def test_started_it_predicts_from_every_observation_written(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    [graph] = received(store, snapshots.ME, PROBE, b'{"value": 0.25}', snapshots.NOW)
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW)
    start(runtime)
    [(kind, predicted)] = runtime.heard
    assert kind == STATE
    assert len(predicted(graph)) == 3, "three stretches: inside, below the floor, below survival"
    assert predicted("http://example.org/test#nothing_made_here") == []

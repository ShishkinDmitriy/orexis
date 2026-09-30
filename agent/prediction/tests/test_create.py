"""Prediction's part: once started it answers every observation a job writes — a graph of the
kernel's state kind holding a node a sensor made, revised by then, belief's part hearing it first —
by rewriting that sensor's predictions, and a graph holding no sensor's node, a silence or a peer's
word, by nothing."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.belief.revise import revise
from agent.ontology import PUBLIC, STATE
from agent.prediction.create import create
from agent.sensing.received import received
from agent.store import close_catalogue, document, graphs_of, put_document

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
PROBE = "http://example.org/test#probe"
AGENT = Path(__file__).parents[2]


def test_its_part_predicts_from_every_observation_written(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    for vocabulary in (AGENT / "sensing" / "rules.ttl", AGENT / "belief" / "ontology.ttl"):
        put_document(store, document(vocabulary))
    [graph] = received(store, snapshots.ME, PROBE, b'{"value": 0.25}', snapshots.NOW)
    revise(store, graph, read=graphs_of(store, PUBLIC))       # as belief's part has, before this hears it
    close_catalogue(store)
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW)
    create(runtime).start(runtime)
    [(kind, predicted)] = runtime.heard
    assert kind == STATE
    assert len(predicted(graph)) == 3, "three stretches: inside, below the floor, below survival"
    assert predicted("http://example.org/test#nothing_made_here") == []

"""Prediction's part: once started it answers every belief a job writes — an observation, a graph
of the kernel's state kind holding a node a sensor made, revised by then, belief's part hearing it
first — by rewriting that sensor's predictions; and a belief holding no sensor's node, a step the
executor committed to, by rewriting every key's, since what a drift reads may have changed."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.belief.revise import revise
from agent.ontology import BELIEF, PUBLIC
from agent.prediction.create import create
from agent.sensing.received import received
from agent.store import close_catalogue, document, entry, graphs_of, put_document, update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
PROBE = "http://example.org/test#probe"
AGENT = Path(__file__).parents[2]
COMMITTED = "http://example.org/test#committed"


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
    assert kind == BELIEF
    assert len(predicted(graph)) == 3, "three stretches: inside, below the floor, below survival"
    #  A BELIEF THAT IS NO SENSOR'S OBSERVATION — a committed step, here a bare graph of the kernel's
    #  kind — rewrites every key's predictions: the probe's three again, and nothing of a key nobody
    #  observed.
    update(store, f"INSERT DATA {{ GRAPH <{COMMITTED}> {{ <{COMMITTED}> <http://example.org/test#says> 1 }} "
                  f"{entry(store, COMMITTED, BELIEF, 'http://example.org/orexis#Recorded', snapshots.ME)} }}")
    assert len(predicted(COMMITTED)) == 3, "every key with an observation in hand, predicted again"

"""Prediction's part: once started it answers every percept a job writes — a graph of sensing's
kind holding a node a sensor made, revised by then, sensing's part handing it to belief's first —
by rewriting that sensor's predictions; and every belief, holding no sensor's node, a step the
executor committed to, by rewriting every key's, since what a flow reads may have changed."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.belief.revise import revise
from agent.ontology import BELIEF
from agent.prediction.create import create
from agent.sensing.ontology import OBSERVATION_GRAPH
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
    revise(store, graph, read=graphs_of(store, BELIEF, common=True), kind=OBSERVATION_GRAPH)   # as sensing has, before this hears it
    close_catalogue(store)
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW)
    create(runtime).start(runtime)
    heard = dict(runtime.heard)
    assert set(heard) == {OBSERVATION_GRAPH, BELIEF}, "a percept is no belief, and is heard by sensing's kind (#944)"
    predicted = heard[OBSERVATION_GRAPH]
    assert len(predicted(graph)) == 3, "three stretches: inside, below the floor, below survival"
    #  A BELIEF THAT IS NO SENSOR'S OBSERVATION — a committed step, here a bare graph of the kernel's
    #  kind — rewrites every key's predictions: the probe's three again, and nothing of a key nobody
    #  observed.
    update(store, f"INSERT DATA {{ GRAPH <{COMMITTED}> {{ <{COMMITTED}> <http://example.org/test#says> 1 }} "
                  f"{entry(store, COMMITTED, BELIEF, 'http://example.org/orexis#Recorded', snapshots.ME)} }}")
    assert len(predicted(COMMITTED)) == 3, "every key with an observation in hand, predicted again"


CHAINED = Path(__file__).parent / "predict" / "a_key_is_predicted_from_another_keys_prediction.trig"
HYGROMETER = "http://example.org/test#hygrometer"
AIR = "http://example.org/orexis/graph/observed/keeper/room_humidity"
SOIL = "http://example.org/orexis/graph/observed/keeper/zamioculcas_moisture"


def _keys(written) -> list[str]:
    """The key each written graph is of, in order, once per run of one key."""
    out = []
    for g in written:
        key = g.rsplit("/", 1)[-1].rsplit("_", 1)[0]
        if not out or out[-1] != key:
            out.append(key)
    return out


def test_one_arrival_walks_the_keys_once_in_the_order_their_drifts_read_each_other(monkeypatch, snapshots, stand_in_runtime):
    """THE WALK (#996). The soil's flow reads the room's humidity, so a belief arriving rewrites the air
    first and the soil after it, each once; the hygrometer's percept arriving rewrites the air and the
    soil, which depends on it; the probe's rewrites the soil alone, since nothing reads the soil; and a
    graph this part wrote itself is answered with nothing, so a prediction heard as a belief (#992)
    rewrites no key and the walk ends."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CHAINED)
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW)
    create(runtime).start(runtime)
    predicted = dict(runtime.heard)[BELIEF]
    update(store, f"INSERT DATA {{ GRAPH <{COMMITTED}> {{ <{COMMITTED}> <http://example.org/test#says> 1 }} "
                  f"{entry(store, COMMITTED, BELIEF, 'http://example.org/orexis#Recorded', snapshots.ME)} }}")
    written = predicted(COMMITTED)
    assert _keys(written) == ["room_humidity", "zamioculcas_moisture"], written
    assert predicted(written[0]) == [] and predicted(written[-1]) == [], "what it wrote, it answers nothing of"
    assert _keys(predicted(AIR)) == ["room_humidity", "zamioculcas_moisture"], "the air, and the soil that reads it"
    assert _keys(predicted(SOIL)) == ["zamioculcas_moisture"], "the soil alone: nothing reads it"

"""Prediction's part: it hears nothing and writes nothing, and what it offers is `foresee` — the
integration of the flows, made fresh from the belief base for a pass, which the planner's part takes at
link and advances as it lays the grounds (a-flow-is-integrated-where-the-ground-is-laid, #1000)."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.belief.revise import revise
from agent.ontology import BELIEF
from agent.prediction.create import create
from agent.sensing.ontology import OBSERVATION_GRAPH
from agent.sensing.received import received
from agent.store import close_catalogue, document, graphs_of, put_document

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
PROBE = "http://example.org/test#probe"
AGENT = Path(__file__).parents[2]


def test_its_part_offers_the_foresight_and_hears_nothing(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    for vocabulary in (AGENT / "sensing" / "rules.ttl", AGENT / "belief" / "ontology.ttl"):
        put_document(store, document(vocabulary))
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW)
    part = create(runtime)
    assert not hasattr(part, "start") or (part.start(runtime) or runtime.heard == []), "it hears no kind: there is nothing to answer with"
    assert part.foresee(store, snapshots.NOW) is None, "no percept in hand: nothing is foreseen"
    [graph] = received(store, snapshots.ME, PROBE, b'{"value": 0.25}', snapshots.NOW)
    revise(store, graph, read=graphs_of(store, BELIEF, common=True), kind=OBSERVATION_GRAPH)   # as sensing has, before a pass
    close_catalogue(store)
    foresight = part.foresee(store, snapshots.NOW)
    assert [k.sensor for k in foresight.keys] == [PROBE], "the probe's key, read off its latest percept"
    assert foresight.keys[0].lo == 0.25 and foresight.keys[0].laid
    #  WHAT A SCOPE LAYS: the keys the caller places there; every key is advanced either way.
    assert not part.foresee(store, snapshots.NOW, placed=lambda feature, prop: False).keys[0].laid
    assert runtime.written == [], "nothing is written into the belief base"

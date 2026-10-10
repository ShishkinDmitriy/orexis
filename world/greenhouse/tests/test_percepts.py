"""The greenhouse's percepts (#944's fourth slice, knowledge/domain/sensing/observation.md): every reading
the grower hears is a percept of its own, of sensing's kind and no kernel's, linked to the one before it,
kept as deep as sensing's stuck rule reads, and handed to no reader of the mind — so none crosses into the
imaginarium a pass searches in, whatever the pass plans, and what crosses of a reading is the state a
transition made of it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox

from agent import clock
from agent.planning.world_at import world_at
from agent.runtime import Runtime, boot
from agent.sensing.received import STUCK_AFTER
from agent.store import graphs_of, revisions_of, rows
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
CADENCE = timedelta(minutes=10)
GH = "http://example.org/orexis/world/greenhouse#"
SOIL, AIR = "sensors/moisture_probe/reading", "sensors/thermometer/reading"
SENSING = "http://example.org/orexis/sensing#"
OBSERVATION_GRAPH = SENSING + "ObservationGraph"

#  WHAT ONLY A PERCEPT SAYS: the number a sensor gave, the link to the one before, what the rules
#  conclude of a sensor from the percepts kept.
_PERCEPT_WORDS = {SENSING + "rawResult", SENSING + "scaledResult", SENSING + "previous", SENSING + "stuckOn"}

#  A SENSOR'S PERCEPTS, oldest first, each with the one it names before it.
_CHAIN_Q = """
SELECT ?o ?previous WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor $sensor ; sosa:resultTime ?t OPTIONAL { ?o sensing:previous ?previous } } }
ORDER BY ?t"""

#  EVERY PERCEPT RECEIVED, told from what was concluded of it — of the same kind — by its arrival.
_RECEIVED_Q = """SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?g a sensing:ObservationGraph ; orexis:arrivedBy orexis:Received } }"""


class _Broker:
    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, json.loads(payload)))


def _grower(monkeypatch):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    broker = _Broker()
    return Runtime(boot(WORLD, "grower"), "grower", transport=Mqtt(GH + "grower", broker)), time, broker


def _passes(runtime, time, readings):
    """Each reading delivered a cadence apart — the soil and the air together — a pass after each."""
    for soil, air in readings:
        runtime.deliver(AIR, json.dumps({"value": air}).encode(), time["at"])
        runtime.deliver(SOIL, json.dumps({"value": soil}).encode(), time["at"])
        runtime.run(passes=1, poll_s=0)
        time["at"] += CADENCE


def test_a_percept_never_crosses_into_the_imaginarium(monkeypatch):
    """Eight readings of a bed drying below its floor and dosed: the pass searches, adopts and lays its
    grounds every time. Not one graph of the imaginaria is a percept or what was concluded of one, not one
    quad there speaks a percept's own word, and the present a pass reads is the state alone — while the
    grounds hold the bed's soil the transitions made, which is what crosses of a reading."""
    runtime, time, broker = _grower(monkeypatch)
    _passes(runtime, time, [(0.25 - n / 1000, 21.0 + n / 100) for n in range(STUCK_AFTER + 2)])
    assert broker.published, "the bed was dosed: a pass searched and found a plan"
    imaginaria = runtime.parts["planning"].planner.imaginaria.values()
    percepts = set(graphs_of(runtime.beliefs, OBSERVATION_GRAPH))
    assert len(percepts) == 2 * 2 * STUCK_AFTER, "two sensors, each its last six and what was concluded of each"
    nodes = {r["o"] for sensor in ("moisture_probe", "thermometer") for r in rows(runtime.beliefs, _CHAIN_Q, (), sensor=GH + sensor)}
    crossed = [(q.graph_name.value, q.predicate.value) for store in imaginaria for q in store
               if q.graph_name.value in percepts or q.predicate.value in _PERCEPT_WORDS
               or (isinstance(q.subject, ox.NamedNode) and q.subject.value in nodes and q.graph_name.value != _catalogue(store))]
    held = [q for store in imaginaria for q in store if q.predicate.value == "http://example.org/orexis/climate#soil"]
    assert held, "the bed's soil crosses, and the search reads it"
    assert not crossed, f"a percept crossed into the imaginarium: {sorted(set(crossed))[:5]}"
    present = world_at(runtime.beliefs, None, now=time["at"] - CADENCE)
    assert not set(present) & percepts, "the present a pass stands in holds no percept"


def test_each_reading_names_the_one_before_it_and_the_last_six_are_kept(monkeypatch):
    runtime, time, _ = _grower(monkeypatch)
    _passes(runtime, time, [(0.45, 21.0 + n / 100) for n in range(STUCK_AFTER + 2)])
    chain = rows(runtime.beliefs, _CHAIN_Q, (), sensor=GH + "thermometer")
    assert len(chain) == STUCK_AFTER
    assert [r.get("previous") for r in chain[1:]] == [r["o"] for r in chain[:-1]], "each names the one before"
    assert chain[0].get("previous") and chain[0]["previous"] not in {r["o"] for r in chain}, "the oldest kept names one forgotten"
    received = [r["g"] for r in rows(runtime.beliefs, _RECEIVED_Q, ())]
    assert len(received) == 2 * STUCK_AFTER, "two sensors, each its last six"
    for graph in received:
        assert len(revisions_of(runtime.beliefs, graph, kind=OBSERVATION_GRAPH)) == 1, \
            "what was concluded of each is kept with it, of its kind, and goes with it"
        assert revisions_of(runtime.beliefs, graph) == [], "and none of it is a belief"


def _catalogue(store) -> str:
    from agent.store import catalogue_of
    return catalogue_of(store)

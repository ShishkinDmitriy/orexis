"""A belief base in memory.

The genesis Turtle is loaded into an rdflib Dataset and queried with the *same* SPARQL the
production code sends to Fuseki — so these tests exercise the real queries against the real
ratified world, with no triplestore running. If a query and the world drift apart, the tests
notice.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import rdflib

from agora import loader, store
from agora.ontology import ONTOLOGY_GRAPH, SENSED_GRAPH, WORLD_GRAPH, beliefs_graph
from agora.seed import agent_id_of

REPO_ROOT = loader.REPO_ROOT
GENESIS_ROOT = REPO_ROOT / "genesis"
GENESIS_DIR = GENESIS_ROOT / "society"   # the world most tests are about


def genesis_dataset(readings: dict[str, float] | None = None,
                    result_time: datetime | None = None,
                    world: str = "society") -> rdflib.Dataset:
    """One seeded belief base — including the DERIVATION step.

    The rules are applied exactly as `agora-seed` applies them, so tests see the capabilities
    the world actually implies rather than a hand-written list. `world` names which of the
    ratified worlds in genesis/ to build, so a test can be about the small one.
    """
    genesis = GENESIS_ROOT / world
    ds = rdflib.Dataset()
    for path in loader.ontology_files():
        ds.graph(rdflib.URIRef(ONTOLOGY_GRAPH)).parse(path, format="turtle")
    ds.graph(rdflib.URIRef(WORLD_GRAPH)).parse(genesis / "world.ttl", format="turtle")
    for path in sorted(genesis.glob("beliefs-*.ttl")):
        graph = rdflib.URIRef(beliefs_graph(agent_id_of(path)))
        ds.graph(graph).parse(path, format="turtle")
    for rule in loader.rule_files():
        ds.update(rule.read_text())

    if readings:
        ts = (result_time or datetime.now(timezone.utc)).isoformat()
        sensed = ds.graph(rdflib.URIRef(SENSED_GRAPH))
        sensed.parse(data="\n".join(
            f"""@prefix agora: <http://example.org/agora#> .
                @prefix sosa: <http://www.w3.org/ns/sosa/> .
                @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
                agora:obs_{pid} a sosa:Observation ;
                  sosa:hasFeatureOfInterest agora:{pid} ;
                  sosa:hasSimpleResult "{value}"^^xsd:decimal ;
                  sosa:resultTime "{ts}"^^xsd:dateTime ."""
            for pid, value in readings.items()
        ), format="turtle")
    return ds


def query_fn(ds: rdflib.Dataset):
    """A QueryFn over the in-memory dataset — prefixed exactly as Store.query prefixes."""

    def query(sparql: str) -> dict:
        return json.loads(ds.query(store.PREFIXES + sparql).serialize(format="json"))

    return query


@pytest.fixture
def query():
    return query_fn(genesis_dataset())


@pytest.fixture
def query_with_readings():
    """Build a query fn over the world plus the given fresh readings."""

    def build(readings, result_time=None):
        return query_fn(genesis_dataset(readings, result_time))

    return build


# --- a live agent over the in-memory belief base ------------------------------------------

class FakeStore:
    """The store interface a module actually uses, backed by the in-memory dataset."""

    def __init__(self, ds: rdflib.Dataset):
        self.ds = ds
        self.query = query_fn(ds)

    def update(self, sparql: str) -> None:
        self.ds.update(store.PREFIXES + sparql)


class Sent(list):
    """Everything the agent put on the wire, so a test can read the conversation."""

    def to(self, topic: str) -> list[dict]:
        return [payload for t, payload, _ in self if t == topic]

    def under(self, prefix: str) -> list[dict]:
        return [payload for t, payload, _ in self if t.startswith(prefix)]

    def topics(self) -> list[str]:
        return [t for t, _, _ in self]


class Msg:
    """The shape paho hands to a callback."""

    def __init__(self, topic: str, payload: dict):
        self.topic = topic
        self.payload = json.dumps(payload).encode()


def build_agent(agent_id: str, ds: rdflib.Dataset | None = None, monkeypatch=None):
    """A real Agent — real world, real beliefs, real modules — with the broker captured.

    Nothing is stubbed except the two things that would reach the network: MQTT and Influx.
    The modules under test are the ones that ship.
    """
    from agora import runtime
    from capabilities.perception import module as perception_module

    class NoInflux:
        def __init__(self, *a, **k):
            pass

        def write_reading(self, *a, **k):
            pass

        def close(self):
            pass

    if monkeypatch is not None:
        monkeypatch.setattr(perception_module, "InfluxWriter", NoInflux)
        monkeypatch.setattr(runtime.mqtt, "Client", lambda *a, **k: _FakeClient())

    agent = runtime.Agent(agent_id, st=FakeStore(ds or genesis_dataset()))
    agent.sent = Sent()
    agent.publish = lambda topic, payload, retain=False: agent.sent.append(
        (topic, payload, retain))
    agent.subscribed = []
    agent._on_connect(_Recorder(agent.subscribed), None, None, 0, None)
    agent.deliver = lambda topic, payload: agent._on_message(None, None, Msg(topic, payload))
    # convenience: reach a module by name, the way a test wants to talk about it
    agent.module = lambda name: next(m for m in agent.modules if m.name == name)
    agent.hosting = lambda: agent.module("hosting")
    agent.bidding = lambda: agent.module("bidding")
    agent.subscribing = lambda: agent.module("subscribing")
    return agent


class _FakeClient:
    def __init__(self, *a, **k):
        self.on_connect = self.on_message = None

    def publish(self, *a, **k):
        pass

    def subscribe(self, *a, **k):
        pass


class _Recorder:
    def __init__(self, into):
        self.into = into

    def subscribe(self, topic):
        self.into.append(topic)

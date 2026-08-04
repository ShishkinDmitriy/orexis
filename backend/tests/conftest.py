"""A belief base in memory — the real one.

Tests build an agent's belief base exactly as an agent does: `genesis.refresh_public` loads the
ratified Turtle and runs the derivation, `genesis.birth` writes opening beliefs. The store is
the production `Store`, in memory rather than on disk, so these tests exercise the real queries
against the real ratified world with nothing stubbed and nothing running.

There is no longer a fake store to drift from the real one, because there is no server to
stand in for.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from agora import genesis, loader
from agora.genesis import agent_id_of
from agora.ontology import SENSED_GRAPH
from agora.store import Store

REPO_ROOT = loader.REPO_ROOT
WORLDS_ROOT = REPO_ROOT / "world"
GENESIS_DIR = WORLDS_ROOT / "society"   # the world most tests are about


def genesis_store(readings: dict[str, float] | None = None,
                  result_time: datetime | None = None,
                  world: str = "society") -> Store:
    """One belief base, built the way an agent builds it — derivation included.

    The rules are applied exactly as an agent applies them, so tests see the capabilities the
    world actually implies rather than a hand-written list. `world` names which of the ratified
    worlds in world/ to build, so a test can be about the small one.
    """
    path = WORLDS_ROOT / world
    st = Store()
    genesis.refresh_public(st, path)
    for beliefs in sorted(path.glob(genesis.BELIEFS_GLOB)):
        genesis.birth(st, path, agent_id_of(beliefs))

    if readings:
        ts = (result_time or datetime.now(timezone.utc)).isoformat()
        st.update("INSERT DATA { GRAPH <%s> {\n%s\n} }" % (SENSED_GRAPH, "\n".join(
            f"""  ag:obs_{pid} a sosa:Observation ;
                    sosa:hasFeatureOfInterest ag:{pid} ;
                    sosa:hasSimpleResult "{value}"^^xsd:decimal ;
                    sosa:resultTime "{ts}"^^xsd:dateTime ."""
            for pid, value in readings.items())))
    return st


def query_fn(st: Store):
    """The QueryFn a reader is written against. It is simply the store's own."""
    return st.query


@pytest.fixture
def query():
    return genesis_store().query


@pytest.fixture
def query_with_readings():
    """Build a query fn over the world plus the given fresh readings."""

    def build(readings, result_time=None):
        return query_fn(genesis_store(readings, result_time))

    return build


# --- a live agent over the in-memory belief base ------------------------------------------

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


def build_agent(agent_id: str, st: Store | None = None, monkeypatch=None):
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

    agent = runtime.Agent(agent_id, st=st or genesis_store())
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

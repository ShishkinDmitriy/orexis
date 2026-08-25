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
from pathlib import Path

import pytest

from agent import genesis, loader
from agent.genesis import agent_id_of
from agent.ontology import SENSED_GRAPH
from packages.capability.sensing.sensed_writer import observation_uri
from agent.store import Store

REPO_ROOT = loader.REPO_ROOT
WORLDS_ROOT = REPO_ROOT / "world"
GENESIS_DIR = WORLDS_ROOT / "simulation"   # the world most tests are about

# The property the water domain is about, spelled out because a reading is now keyed by it.
MOISTURE = "http://example.org/orexis/water#SoilMoisture"
# Two more, for the tests that are about a subject with more than one property. HUMIDITY is
# the pointed one: it is a fraction, so a reading of it is indistinguishable from a soil
# moisture by inspection, and a bidder handed one will act on it.
TEMPERATURE = "http://example.org/orexis/water#AirTemperature"
HUMIDITY = "http://example.org/orexis/water#AirHumidity"


@pytest.fixture(autouse=True)
def name_the_world(monkeypatch):
    """Tests run outside a container, so they must name their world like any other caller.

    There is no default world — `genesis.current_world` refuses rather than guessing, because a
    process that was not told which world it belongs to is misconfigured. These tests are about
    the simulation, and anything under test that resolves signing keys finds them through it. The
    line above said so already; this makes the code hear it.
    """
    monkeypatch.setenv("OREXIS_WORLD", GENESIS_DIR.name)
    # And run KEYLESS, whatever this machine's worlds carry. `orexis-keygen` writes a real
    # keys.ttl into the repo's world directories (gitignored, present wherever an operator has
    # onboarded), and `world_files` sweeps every .ttl — so on an operator's machine claims
    # seal, presentations demand signatures, and any test reading a plaintext payload fails
    # HERE while passing in CI. A test that needs keys injects roster triples explicitly
    # (test_signed_and_sealed does); everything else must see the world as the files in git
    # describe it, not as this machine last deployed it.
    real = genesis.world_files
    monkeypatch.setattr(genesis, "world_files",
                        lambda world: [p for p in real(world) if p.name != "keys.ttl"])


def genesis_store(readings: dict[str, float] | None = None,
                  result_time: datetime | None = None,
                  world: str = "simulation") -> Store:
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
        # The subject lives in the WORLD's namespace since a world took its individuals out
        # of ag: — a seeded reading must point where the world's fern actually is.
        ns = f"http://example.org/orexis/world/{world}#"
        ts = (result_time or datetime.now(timezone.utc)).isoformat()
        st.update("INSERT DATA { GRAPH <%s> {\n%s\n} }" % (SENSED_GRAPH, "\n".join(
            f"""  {observation_uri(pid, prop)} a sosa:Observation ;
                    sosa:hasFeatureOfInterest <{ns}{pid}> ;
                    sosa:observedProperty <{prop}> ;
                    {_made_by(st, f"{ns}{pid}", prop)}
                    sosa:hasSimpleResult "{value}"^^xsd:decimal ;
                    sosa:resultTime "{ts}"^^xsd:dateTime ."""
            for (pid, prop), value in _by_subject_and_property(readings).items())))
    return st


def _made_by(st: Store, subject: str, observed_property: str) -> str:
    """`sosa:madeBySensor <the instrument this world says watches that pair>`, or nothing.

    A seeded reading has to look like one the production writer would have produced, and this
    is the clause it was missing: `sensed_writer` states the sensor unconditionally, and the
    freshness want asks for a reading made by ITS instrument — a want about an observation
    that names nobody would be satisfied by a prediction of what a dose would do. Discovered
    from the world rather than passed in, so a test seeds what the wiring implies.

    Empty where the world states no such sensor, which stays a legal thing for a test to seed:
    a subject nobody watches can still be given a reading, and it will simply satisfy no
    epistemic want, which is the truth about it.
    """
    rows = st.query(
        f"SELECT ?s WHERE {{ ?s sensing:monitors <{subject}> ; sosa:observes "
        f"<{observed_property}> }} LIMIT 1")["results"]["bindings"]
    return f"sosa:madeBySensor <{rows[0]['s']['value']}> ;" if rows else ""


def _by_subject_and_property(readings: dict) -> dict[tuple[str, str], float]:
    """`{"fern": 0.18}` means moisture; `{("fern", TEMPERATURE): 21.0}` says which.

    Written through `observation_uri`, the same function the writer mints with, so a test can
    never seed a node the production code would not have produced.
    """
    return {(k, MOISTURE) if isinstance(k, str) else k: v for k, v in readings.items()}


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
    from agent import runtime
    from packages.capability.sensing import observation

    class NoInflux:
        def __init__(self, *a, **k):
            pass

        def write_reading(self, *a, **k):
            pass

        def close(self):
            pass

    if monkeypatch is not None:
        # one place for every capability that records — see orexis/observation.py
        monkeypatch.setattr(observation, "InfluxWriter", NoInflux)
        monkeypatch.setattr(runtime.mqtt, "Client", lambda *a, **k: _FakeClient())
        # What a deployed agent is handed: its OWN bucket and a token that opens only it,
        # mounted into its container by `orexis-influx`. Set here rather than defaulted in the
        # code, because a fallback to a shared bucket is exactly the isolation failure the
        # per-agent credential exists to prevent — so the agent refuses to run without one,
        # and the fixture has to say what it was given like any other deployment would.
        monkeypatch.setenv("INFLUX_BUCKET", f"test-{agent_id}")
        monkeypatch.setenv("INFLUX_TOKEN", f"test-token-{agent_id}")

    st = st or genesis_store()
    # What `open_belief_base` does for a deployed agent and a bare genesis store lacks: the
    # agent's own graphs say what they ARE, which is how the mind's build selects them.
    genesis.classify_own_graphs(st, agent_id)
    agent = runtime.Agent(agent_id, st=st)
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
    agent.reviewing = lambda: agent.module("review")
    #  WHAT IT TREATS AS STALE, which a booted agent always knows and a built one did not.
    #  `SensingModule.start()` writes the horizon per sensor and nothing else here calls
    #  `start` — so a fixture agent had none, and the want that asks whether a reading is
    #  still evidence could not be repaired by looking: with no horizon there is no "recent
    #  enough" for a predicted reading to be inside, so the search reported that nothing
    #  helps and a bidder sat every round out. This is the one line of `start` with no
    #  message on the wire, so it can be run here without the cadence traffic a full start
    #  would add to every test that reads what was published.
    for module in agent.modules:
        if hasattr(module, "publish_horizon"):
            module.publish_horizon()
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


def desires_build(st: Store, agent_id: str):
    """One agent's desire modality over a genesis store — what a test asks for wants (#312).

    The belief base holds no wants any more; a test that reads regions, gaps or the whole
    pursuit list builds the modality the way the agent's boot does, and asks it.
    """
    from agent.beliefs import Beliefs
    from agent.desire import Desires

    return Desires(Beliefs(st, agent_id))


def open_round_for(st_or_agent, agent_id: str, seconds: float = 60.0) -> list[str]:
    """A round open on every venue this agent bids in — the fact, written as the wire would.

    Since #358 the buying row exists only while a round is open, so a test asking what a
    plant could do, or whether it would buy, has to say a round is open first. Written through
    the market's own writer into the agent's own graph, exactly as `on_offer` writes it; a
    bare store gets a stand-in with the two things the writer reads.
    """
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    from agent.store import bindings
    from packages.capability.market import rounds

    st = getattr(st_or_agent, "beliefs", st_or_agent)
    agent = st_or_agent if hasattr(st_or_agent, "beliefs") else SimpleNamespace(beliefs=st, id=agent_id)
    venues = [r["v"] for r in bindings(st.query(
        f'SELECT ?v WHERE {{ ?a ag:localId "{agent_id}" ; market:bidsIn ?v }}'))]
    closes = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return [rounds.open_round(agent, v, f"test-{agent_id}-{i}", 2.0, 0.4, closes)
            for i, v in enumerate(venues)]


# --- what an agent is WIRED TO, since it left `Self` (self-is-bdi-and-wiring-is-the-packages) ---
#
# `agent.me` is what an agent IS; its sensors, actuators and venues are each package's to load.
# A test that reaches for them reaches through the package's own wiring loader, exactly as the
# module does — and these are the one-liners so a test says `wired_sensors(fern)` and not the
# query surface and the agent's URI every time.

def sensing_of(agent):
    """The agent's sensing module — where its regions, gaps and stakes live now
    (the-stake-is-sensings-want). A test that used to ask `agent.deducer` asks this."""
    return next((m for m in agent.modules if hasattr(m, "regions")), _NoSensing())


class _NoSensing:
    """An agent that senses nothing — the city — holds no region, sees no gap, wants nothing
    about a reading. Said as an empty module rather than as None, so a test can ask."""
    regions: dict = {}

    def aim(self, observed_property):
        return None

    def gaps(self):
        return {}

    def desires(self, now=None):
        return []


def stake_of(agent, observed_property=None):
    """The region want an agent holds about a property — the node the ledger keys on now."""
    from conftest import MOISTURE as _M
    return sensing_of(agent).stake_about(observed_property or _M)


def wired_sensors(agent):
    from packages.capability.sensing.wiring import sensors_of
    return sensors_of(agent.beliefs.query, agent.me.uri)


def wired_actuators(agent):
    from packages.capability.actuation.wiring import actuators_of
    return actuators_of(agent.beliefs.query, agent.me.uri)


def wired_actuator_for(agent, subject_id: str):
    from packages.capability.actuation.wiring import actuator_for
    return actuator_for(wired_actuators(agent), subject_id)


def wired_markets(agent):
    from packages.capability.market.wiring import bidding_markets_of
    return bidding_markets_of(agent.beliefs.query, agent.me.uri)


def wired_hosted_markets(agent):
    from packages.capability.market.wiring import hosted_markets_of
    return hosted_markets_of(agent.beliefs.query, agent.me.uri)


def load_wired(query, agent_id: str):
    """`load_self` plus the wiring every package would load for this agent — for a test that
    reads sensors, actuators or venues off a bare store without building an agent. A
    composite the kernel deliberately no longer has; tests are the one place it is wanted."""
    from types import SimpleNamespace

    from agent.world import load_self
    from packages.capability.actuation.wiring import actuator_for, actuators_of
    from packages.capability.market.wiring import bidding_markets_of, hosted_markets_of
    from packages.capability.sensing.wiring import sensors_of

    me = load_self(query, agent_id)
    actuators = actuators_of(query, me.uri)
    return SimpleNamespace(
        actuator_for=lambda subject_id: actuator_for(actuators, subject_id),
        uri=me.uri, agent_id=me.agent_id, capabilities=me.capabilities, can=me.can,
        acts_for=me.acts_for, acts_for_id=me.acts_for_id,
        sensors=sensors_of(query, me.uri), actuators=actuators,
        markets=bidding_markets_of(query, me.uri), hosted_markets=hosted_markets_of(query, me.uri))


def wired_event_topic(agent):
    from packages.capability.sensing.wiring import event_topic_of
    return event_topic_of(agent.beliefs.query, agent.me.uri)


def reading_of(agent, observed_property: str, subject_uri: str | None = None):
    """The newest reading an agent holds of one property — through the sensing provider, since
    what a reading looks like is sensing's (the-stake-is-sensings-want)."""
    sensing = agent.provider("http://example.org/orexis/sensing#SensingCapability")
    return sensing.current_reading(subject_uri or agent.me.acts_for, observed_property)


def write_reading(agent, value: float, observed_property: str | None = None, age_s: float = 0):
    """Put one reading of the agent's subject in its sensed graph, through the production
    writer — so the observation carries the sensor that made it. Since readings are sensing's
    (the-stake-is-sensings-want) a want's `value` is not the world; the world is."""
    from datetime import datetime, timedelta, timezone

    from packages.capability.sensing.sensed_writer import SensedWriter

    sensors = wired_sensors(agent)
    sensor = next(s for s in sensors if observed_property is None or s.observes == observed_property)
    SensedWriter(agent.beliefs).write(
        subject_uri=sensor.subject, subject_id=sensor.subject.rsplit("#", 1)[-1],
        value=value, sensor_uri=sensor.uri, observed_property=sensor.observes,
        author_uri=agent.me.uri, used_procedure=sensor.sense_mode,
        ts=(datetime.now(timezone.utc) - timedelta(seconds=age_s)).isoformat())

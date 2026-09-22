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

from agent import genesis

from assembly import loader
from agent.genesis import agent_id_of
from orexis_agent_progression import clock   # the agent's timeline, which a test helper speaks in
from orexis_agent_progression.ontology import STATE_GRAPH
from orexis_capability_sensing.sensed_writer import observation_uri
from orexis_agent_progression.store import Store
from orexis_agent_progression.ontology import PUBLIC

REPO_ROOT = loader.REPO_ROOT
WORLDS_ROOT = REPO_ROOT / "world"
GENESIS_DIR = WORLDS_ROOT / "simulation"   # the world most tests are about


def shipped_worlds() -> list[str]:
    """Every ratified world, FOUND BY LOOKING — the one roster, so a new one is covered at once.

    `test_shapes.py` already said this in its own words — *found by looking, never listed* — and
    two files did not follow: `test_provenance.py` and `test_isolation.py` each hard-coded
    `["simulation", "sensing"]`, written on 2026-08-09 and 2026-08-07. `world/loner` arrived on
    2026-08-18 and got none of the eleven parametrised tests between them, for as long as it has
    existed. It passes all eleven; that is luck, and the nine days were silent.

    A directory with no world files is not a world, which is what keeps a stray `world/society/`
    holding nothing but an orphaned `secrets/` out of the roster without anybody listing it.
    """
    from agent import genesis

    return sorted(d.name for d in WORLDS_ROOT.iterdir() if genesis.world_files(d))

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
        # of orexis: — a seeded reading must point where the world's fern actually is.
        ns = f"http://example.org/orexis/world/{world}#"
        ts = (result_time or clock.now()).isoformat()
        st.update("INSERT DATA { GRAPH <%s> {\n%s\n} }" % (STATE_GRAPH, "\n".join(
            f"""  {observation_uri(pid, prop)} a sosa:Observation ;
                    sosa:hasFeatureOfInterest <{ns}{pid}> ;
                    sosa:observedProperty <{prop}> ;
                    {_made_by(st, f"{ns}{pid}", prop)}
                    sosa:hasSimpleResult "{value}"^^xsd:decimal ;
                    sosa:resultTime "{ts}"^^xsd:dateTime ."""
            for (pid, prop), value in _by_subject_and_property(readings).items())))
        st.entail(STATE_GRAPH)        # what the seeded readings ARE, as a boot would say (#576)
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
        f"<{observed_property}> }} LIMIT 1", st.graphs_of(PUBLIC))["results"]["bindings"]
    return f"sosa:madeBySensor <{rows[0]['s']['value']}> ;" if rows else ""


def _by_subject_and_property(readings: dict) -> dict[tuple[str, str], float]:
    """`{"fern": 0.18}` means moisture; `{("fern", TEMPERATURE): 21.0}` says which.

    Written through `observation_uri`, the same function the writer mints with, so a test can
    never seed a node the production code would not have produced.
    """
    return {(k, MOISTURE) if isinstance(k, str) else k: v for k, v in readings.items()}


def query_fn(st: Store):
    """The QueryFn a reader is written against. It is simply the store's own."""
    return st.reader(PUBLIC)


@pytest.fixture
def query():
    return genesis_store().reader(PUBLIC)


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


def build_agent(agent_id: str, st: Store | None = None, monkeypatch=None, *,
                validating: bool = False):
    """A real Agent — real world, real beliefs, real modules — with the broker captured.

    Nothing is stubbed except the two things that would reach the network: MQTT and Influx.
    The modules under test are the ones that ship.

    AND THE BOOT GATE IS NOT RUN unless a test asks (`validating=True`). `validate_agent`
    holds the agent's beliefs to its capabilities' shapes at boot — a check that raises or
    passes and changes nothing else — and it cost two seconds of every boot here: the store
    flattened into rdflib, skolemised, serialised and judged, about 250 times a run, to say
    the same thing every time about a store built from the ratified files. The gate is the
    SUBJECT of `test_validate`, `test_shapes` and the tests that build an `Agent` themselves;
    everywhere else it was the price of the fixture. Measured: a fern boot 2.35 s with it,
    0.3 s without.
    """
    from contextlib import nullcontext
    from unittest import mock

    from agent import runtime

    class NoInflux:
        def __init__(self, *a, **k):
            pass

        def write_reading(self, *a, **k):
            pass

        def close(self):
            pass

    if monkeypatch is not None:
        #  No series sink: reporting builds its writer in `start()`, which a built agent never
        #  runs, so `record` is told and nobody writes — exactly a deployment with no credential.
        #  The transport's client, captured — the module is real, its socket is not.
        from orexis_transport_mqtt import module as mqtt_module
        monkeypatch.setattr(mqtt_module.mqtt, "Client", lambda *a, **k: _FakeClient())
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
    genesis.classify_kernel_graphs(st, agent_id)
    with (nullcontext() if validating
          else mock.patch.object(runtime, "validate_agent", lambda *a, **k: None)):
        agent = runtime.Agent(agent_id, st=st)
    # convenience: reach a module by name, the way a test wants to talk about it
    agent.module = lambda name: next(m for m in agent.modules if m.name == name)
    #  The wire, read through the transport's captured client: everything sent, and every
    #  channel asked for at connect. The kernel has no mailbox, so the transport module is
    #  where a test speaks to the society from.
    link = agent.module("mqtt")
    agent.sent = Sent()
    link.client.sent = agent.sent
    agent.subscribed = link.client.subscribed
    link._on_connect()
    #  DELIVER AND SETTLE. A message is reactive: it marks what moved and returns, and the
    #  pass runs on a thread of the mind's own (#392). A test wants the consequences before it
    #  asserts, so this waits for that thread — which is not this one, which is what
    #  `tests/test_hooks.py` holds the reactive row to.
    def deliver(topic, payload):
        link._on_message(topic, Msg(topic, payload).payload)
        agent.reviser.settle()

    agent.deliver = deliver
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
    #  AND PREDICTS WHAT IT HOLDS (#643), as `start()` re-arms every standing reading: a
    #  built agent's predictions are what a booted one's are, so a crossing can be read.
    for module in agent.modules:
        if hasattr(module, "repredict"):
            module.repredict()
    agent.upkeep.sweep()          # as boot does: what is outdated is gone before the first pass (#645)
    return agent


class _FakeClient:
    """Paho, captured: what was published lands in `sent` as (topic, dict, retain), what was
    subscribed in `subscribed`, and nothing reaches the network. `_thread` is what the
    watchdog's corpse check reads — absent until a test plants one, as on a client that never
    started its loop."""
    def __init__(self, *a, **k):
        self.on_connect = self.on_disconnect = self.on_message = None
        self.sent: list = []
        self.subscribed: list = []

    def publish(self, topic, payload, qos=1, retain=False):
        self.sent.append((topic, json.loads(payload), retain))

    def subscribe(self, topic):
        self.subscribed.append(topic)


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
    from orexis_agent_deliberation.beliefs import Beliefs
    from orexis_agent_deliberation.desires import Desires

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

    from orexis_agent_progression.store import bindings
    from orexis_capability_market import rounds

    st = getattr(st_or_agent, "beliefs", st_or_agent)
    #  A bare store gets a stand-in with what the writer reads: the store, the id, and who I
    #  am — the writer says whose graph it writes.
    me = next(iter(bindings(st.query(
        f'SELECT ?a WHERE {{ ?a a orexis:Agent ; orexis:localId "{agent_id}" }} LIMIT 1', st.graphs_of(PUBLIC)))), {}).get("a")
    agent = (st_or_agent if hasattr(st_or_agent, "beliefs")
             else SimpleNamespace(beliefs=st, id=agent_id, me=SimpleNamespace(uri=me)))
    venues = [r["v"] for r in bindings(st.query(
        f'SELECT ?v WHERE {{ ?a orexis:localId "{agent_id}" ; market:bidsIn ?v }}', st.graphs_of(PUBLIC)))]
    closes = clock.now() + timedelta(seconds=seconds)
    return [rounds.open_round(agent, v, f"test-{agent_id}-{i}", 2.0, 0.4, closes)
            for i, v in enumerate(venues)]


# --- what an agent is WIRED TO, since it left `Self` (self-is-bdi-and-wiring-is-the-packages) ---
#
# `agent.me` is what an agent IS; its sensors, actuators and venues are each package's to load.
# A test that reaches for them reaches through the package's own wiring loader, exactly as the
# module does — and these are the one-liners so a test says `wired_sensors(fern)` and not the
# query surface and the agent's URI every time.

def sensing_of(agent):
    """The agent's sensing module — where its regions, gaps and region wants live now
    (the-region-want-is-sensings-want). A test that used to ask `agent.deducer` asks this."""
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


def region_want_of(agent, observed_property=None):
    """The region want an agent holds about a property — the node the ledger keys on now."""
    from conftest import MOISTURE as _M
    return sensing_of(agent).region_want_about(observed_property or _M)


def wired_sensors(agent):
    from orexis_capability_sensing.wiring import sensors_of
    return sensors_of(agent.beliefs.reader(PUBLIC), agent.me.uri)


def wired_actuators(agent):
    from orexis_capability_actuation.wiring import actuators_of
    return actuators_of(agent.beliefs.reader(PUBLIC), agent.me.uri)


def wired_actuator_for(agent, subject_id: str):
    from orexis_capability_actuation.wiring import actuator_for
    return actuator_for(wired_actuators(agent), subject_id)


def wired_markets(agent):
    from orexis_capability_market.wiring import bidding_markets_of
    return bidding_markets_of(agent.beliefs.reader(PUBLIC), agent.me.uri)


def wired_hosted_markets(agent):
    from orexis_capability_market.wiring import hosted_markets_of
    return hosted_markets_of(agent.beliefs.reader(PUBLIC), agent.me.uri)


def load_wired(query, agent_id: str):
    """`load_self` plus the wiring every package would load for this agent — for a test that
    reads sensors, actuators or venues off a bare store without building an agent. A
    composite the kernel deliberately no longer has; tests are the one place it is wanted."""
    from types import SimpleNamespace

    from agent.world import load_self
    from orexis_capability_actuation.wiring import actuator_for, actuators_of
    from orexis_capability_market.wiring import bidding_markets_of, hosted_markets_of
    from orexis_capability_sensing.wiring import sensors_of

    me = load_self(query, agent_id)
    actuators = actuators_of(query, me.uri)
    return SimpleNamespace(
        actuator_for=lambda subject_id: actuator_for(actuators, subject_id),
        uri=me.uri, agent_id=me.agent_id, capabilities=me.capabilities, can=me.can,
        acts_for=me.acts_for, acts_for_id=me.acts_for_id,
        sensors=sensors_of(query, me.uri), actuators=actuators,
        markets=bidding_markets_of(query, me.uri), hosted_markets=hosted_markets_of(query, me.uri))


def wired_event_topic(agent):
    from orexis_capability_sensing.wiring import event_topic_of
    return event_topic_of(agent.beliefs.reader(PUBLIC), agent.me.uri)


def reading_of(agent, observed_property: str, subject_uri: str | None = None):
    """The newest reading an agent holds of one property — through the sensing provider, since
    what a reading looks like is sensing's (the-region-want-is-sensings-want)."""
    sensing = agent.provider("http://example.org/orexis/sensing#SensingCapability")
    return sensing.current_reading(subject_uri or agent.me.acts_for, observed_property)


def write_reading(agent, value: float, observed_property: str | None = None, age_s: float = 0):
    """Put one reading of the agent's subject in its sensed graph, through the production
    writer — so the observation carries the sensor that made it. Since readings are sensing's
    (the-region-want-is-sensings-want) a want's `value` is not the world; the world is."""
    from datetime import datetime, timedelta, timezone

    from orexis_capability_sensing.sensed_writer import SensedWriter

    sensors = wired_sensors(agent)
    sensor = next(s for s in sensors if observed_property is None or s.observes == observed_property)
    SensedWriter(agent.beliefs).write(
        subject_uri=sensor.subject, subject_id=sensor.subject.rsplit("#", 1)[-1],
        value=value, sensor_uri=sensor.uri, observed_property=sensor.observes,
        author_uri=agent.me.uri, used_procedure=sensor.sense_mode,
        ts=(clock.now() - timedelta(seconds=age_s)).isoformat())
    #  AND SENSING IS TOLD (#639), as the production writer tells it: a reading recorded is
    #  what every standing step that predicted it is compared with, once, here.
    for module in agent.providers("http://example.org/orexis/sensing#SensingCapability"):
        module.on_reading_recorded(sensor.subject, sensor.observes, value)
    #  AND WHETHER THE AGENT STILL TRUSTS IT (#598). A reading is stale because sensing said
    #  so ON the reading, by a deadline landing on the loop — not because its timestamp is
    #  old, which nothing reads as an age any more. `ingest` arms that deadline in production
    #  and `start()` re-arms from what stands; a test writing through the writer alone gets
    #  neither, so the module is asked here to look at what it now holds. An `age_s` past the
    #  horizon is then marked at once, which is what a caller writing one OLD is asking for.
    for module in agent.modules:
        if hasattr(module, "watch_staleness"):
            module.watch_staleness(sensor.subject, sensor.observes)


def predicted_reading(subject_uri: str, observed_property: str, value: float = None,
                      band: str = None) -> tuple:
    """A step's prediction of one reading, in the canonical fact form the search states it in
    (`signature.facts`) — what `progression:predicts` holds for a dose. For tests that adopt a
    step by hand and still want a watch on its end (#510): (adds, retracts). A shipped rule
    predicts the BAND the reading becomes (#579), which `band` states; a `value` is a number a
    caller states by hand, and the world is held to it exactly."""
    SOSA = "http://www.w3.org/ns/sosa/"
    TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    key = ((SOSA + "hasFeatureOfInterest", subject_uri), (SOSA + "observedProperty", observed_property))
    carried = (TYPE, band) if band is not None else (SOSA + "hasSimpleResult", value)
    return (frozenset({("keyed", SOSA + "Observation", key) + carried}), frozenset())


def predicted_bands(agent, step_uri: str) -> list[str]:
    """The classes a ledger step predicts its reading to be (#579) — the band and its families."""
    from orexis_agent_progression.act import predicts_from_json
    from orexis_agent_progression.store import bindings
    rows = bindings(agent.intentions.query_union(
        f"SELECT ?p WHERE {{ <{step_uri}> <http://example.org/orexis/progression#predicts> ?p }}"))
    if not rows:
        return []
    adds, _ = predicts_from_json(rows[0]["p"])
    return sorted(str(f[4]) for f in adds if f[0] == "keyed" and f[3].endswith("#type"))


def predicted_readings(agent, step_uri: str) -> list[float]:
    """The readings a ledger step predicts — the values under `progression:predicts`."""
    from orexis_agent_progression.act import predicts_from_json
    from orexis_agent_progression.store import bindings
    rows = bindings(agent.intentions.query_union(
        f"SELECT ?p WHERE {{ <{step_uri}> <http://example.org/orexis/progression#predicts> ?p }}"))
    if not rows:
        return []
    adds, _ = predicts_from_json(rows[0]["p"])
    return [float(f[4]) for f in adds if f[0] == "keyed" and f[3].endswith("hasSimpleResult")]


#  WHAT ACTIONS ARE FILLED WITH, for tests that build a step or read a row. Each is a parameter
#  some package declares its action `orexis:takes`; the kernel has no column for any of them, so
#  a test names the one it means exactly as the taker does.
ABOUT = "http://example.org/orexis#about"
VENUE = "http://example.org/orexis/market#venue"
DIRECTION = "http://example.org/orexis/market#direction"
VALVE = "http://example.org/orexis/actuation#valve"
SENSOR = "http://example.org/orexis/sensing#sensor"
DISK = "http://example.org/orexis/hanoi#disk"
ONTO = "http://example.org/orexis/hanoi#onto"


def filled(*pairs) -> tuple[tuple[str, str], ...]:
    """A binding, out of (parameter, value) pairs — sorted, as every binding is, and dropping
    any whose value is absent."""
    return tuple(sorted((p, v) for p, v in pairs if v is not None))


def weighed(planner) -> list[dict]:
    """What a pass weighed, asked of the pass graph it wrote: one row per candidate, with the
    action it would take, the verdict and the depth.

    A READ, not an accessor. The planner kept a Python list of these until the verdict came to
    be written where it is decided; a test that wants to know what was weighed asks the store,
    exactly as the trace does.
    """
    from orexis_agent_deliberation.imaginarium import PASS_GRAPH
    from orexis_agent_progression.store import bindings
    if getattr(planner, "imaginarium", None) is None or getattr(planner, "_want", None) is None:
        return []
    rows = bindings(planner.imaginarium.query_over(f"""
SELECT ?action ?verdict ?depth WHERE {{
  ?x a deliberation:Weighing ; deliberation:forWant <{planner._want}> ;
     deliberation:weighs ?c ; deliberation:verdict ?verdict ; deliberation:atDepth ?depth .
  ?c deliberation:wouldTake ?action }}""", PASS_GRAPH))
    return [dict(r, depth=int(r["depth"])) for r in rows]

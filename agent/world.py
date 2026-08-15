"""The world — public topology and composed capabilities. Everything is found, nothing named.

An agent process is handed exactly one instance identifier: its own id. From that it reads
this graph and learns what it *is* — what it acts for, what it may poll, which market it
belongs to, what it can do — and where every one of those things lives on the wire.

Two rules hold throughout this module:

- **Discovery by term, never by name.** The world is found by `?w a ag:World`, the market by
  `market:bidsIn`, the supplier by whoever hosts. No query mentions an instance.
- **No defaults for anything the graph should state.** A missing topic or a missing capability
  parameter is a genesis error, and it fails loudly at startup rather than quietly at 3am.
  The SHACL modules exist to catch it before that.

See knowledge/decisions/capability-modules.md, knowledge/decisions/world-graph.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ontology import WORLD_GRAPH
from .store import QueryFn, bindings


class WorldError(RuntimeError):
    """The world does not say something the code needs. Genesis is wrong, not the runtime."""


@dataclass(frozen=True)
class MessageBus:
    """A broker the society meets on. In the world, because a channel name means nothing
    without it and members who disagree about the bus are not in one society."""

    uri: str
    host: str
    port: int
    # Optional second door on the SAME bus, where a principal proves itself with a certificate
    # instead of a password. None means this world has no mTLS listener and everyone uses the
    # port above. It is not a different bus: same topics, same ACL, same society.
    tls_port: int | None = None


@dataclass(frozen=True)
class Sensor:
    """A device an agent may read, plus whatever its binding states about reaching it.

    The binding fields are optional on purpose: a self-clocked device has no command channel,
    and a device on some other transport would carry different fields entirely. Which driver
    speaks to it is decided from these — never from anything the agent believes.
    """

    uri: str
    local_id: str
    subject: str  # URI of what it monitors
    subject_id: str
    observes: str  # URI of the property it reads
    # WHO HOLDS THE CLOCK — sensing:ScheduledProcedure keeps an interval it is given, sensing:PushProcedure keeps its own.
    # The derivation already reads this to decide whether the agent gains sensing:Subscribing or
    # sensing:Listening; carrying it here is what lets the runtime partition what the derivation
    # separated. Without it an agent holding one of each gave both to both modules, and the
    # scheduled sensor's cadence was silently never re-aimed.
    sense_mode: str | None = None
    bus: str | None = None  # URI of the bus it declares itself on, if any
    reading_topic: str | None = None
    # WHICH value in that payload is mine — a JSON Pointer, and None means the default. Two
    # sensors on one board share a topic and differ only here: the board is one MQTT client
    # with one credential, so it sends one message and each sensor takes its own field.
    reading_pointer: str | None = None
    command_topic: str | None = None
    # The two ends of the pipeline the pointer sits in the middle of. Both are DERIVED — genesis
    # writes them from what the world stated, or from its silence — so neither is ever None in a
    # world that has been through genesis, and a shape refuses one that is.
    decoded_by: str | None = None     # which codec — codec:decodedBy
    scaled_by: str | None = None  # which calibration — scaling:scaledBy
    # What unit that quantity is in, as a QUDT IRI. Not the same kind of fact as the two above:
    # they choose an implementation, this states what the number MEANS. A board reporting soil
    # moisture 0.183 and air humidity 0.46 sends two numbers that look identical, and nothing but
    # this says they are the same dimension while 21.4 degrees is not.
    quantity_unit: str | None = None
    # The PATCH this probe actually sits in, when someone judged the pot's soil not one thing
    # (#98): a sosa:Sample whose isSampleOf is the subject above. Optional, and its absence is
    # the ordinary rig — the subject is the feature, and everything reads as it always did.
    sample: str | None = None
    # THIS channel is watched for crossings (#151): its band is commanded beside the cadence,
    # and silence between heartbeats means "nothing crossed" — information. Per sensor, because
    # which values a board can watch is a per-channel hardware fact.
    crossing: bool = False


@dataclass(frozen=True)
class Actuator:
    """A device an agent may drive, with its own calibration and hard cap."""

    uri: str
    local_id: str
    subject: str
    subject_id: str
    command_topic: str
    ml_per_second: float
    max_dose_ml: float
    # Where the device says what it actually dispensed. OPTIONAL because a world may wire a
    # valve it cannot hear back from, and that is a real deployment rather than an error — but
    # an agent with no status channel cannot tell a delivered dose from a refused one, which is
    # what `ActuationModule` reports when it is missing.
    status_topic: str | None = None


@dataclass(frozen=True)
class Market:
    """A venue and its three channels."""

    uri: str
    local_id: str
    resource: str  # URI of what is allocated
    offer_topic: str
    bid_topic: str
    claim_topic: str
    redeem_topic: str | None = None  # absent in a world authored before #132 — paper, unspendable
    capacity_l: float = 0.0  # physical ceiling of the resource — the allocation limit


@dataclass
class Self:
    """What an agent is, from the world's point of view. Its own row, and no one else's."""

    uri: str
    agent_id: str
    capabilities: frozenset[str]
    acts_for: str | None = None  # URI of the subject it advances
    acts_for_id: str | None = None
    event_topic: str | None = None
    sensors: tuple[Sensor, ...] = ()
    actuators: tuple[Actuator, ...] = ()
    markets: tuple[Market, ...] = ()  # bids in
    hosted_markets: tuple[Market, ...] = ()

    def can(self, capability: str) -> bool:
        return capability in self.capabilities

    def actuator_for(self, subject_id: str) -> Actuator | None:
        return next((a for a in self.actuators if a.subject_id == subject_id), None)


@dataclass
class World:
    version: int


_BUS_Q = f"""
SELECT ?bus ?host ?port ?tlsPort WHERE {{ 
  ?bus a mqtt:MessageBus ; mqtt:brokerHost ?host ; mqtt:brokerPort ?port .
  OPTIONAL {{ ?bus mqtt:brokerTlsPort ?tlsPort }}  }}"""

_VERSION_Q = f"""
SELECT ?v WHERE {{ 
  ?world a ag:World ; ag:currentVersion/ag:versionNumber ?v  }} LIMIT 1"""


def _self_q(agent_id: str) -> str:
    """Find me by my id — the only instance identifier the process is given."""
    return f"""
SELECT ?agent ?capability ?actsFor ?actsForId ?eventTopic WHERE {{ 
  ?agent a ag:Agent ; ag:localId "{agent_id}" ; ag:hasCapability ?capability .
  OPTIONAL {{ ?agent ag:actsFor ?actsFor . OPTIONAL {{ ?actsFor ag:localId ?actsForId }} }}
  OPTIONAL {{ ?agent mqtt:eventTopic ?eventTopic }}
 }}"""


def _sensors_q(agent_uri: str) -> str:
    """My sensors and their bindings. The binding parts are OPTIONAL: what a device states
    about how to reach it varies by transport, and a driver is picked from what is there."""
    return f"""
SELECT ?sensor ?localId ?subject ?subjectId ?observes ?senseMode ?bus ?readingTopic
       ?readingPointer ?commandTopic ?decodedBy ?scaledBy ?quantityUnit ?sample ?crossing
WHERE {{
  <{agent_uri}> sensing:polls ?sensor .
  ?sensor ag:localId ?localId ; sensing:monitors ?subject ; sosa:observes ?observes .
  # The mode is the DEVICE's (#96), reached through the stream the sensor shares with it —
  # a peripheral has no clock of its own, and its board's answer is the only answer there is.
  OPTIONAL {{ ?sensor mqtt:readingTopic ?stream .
              ?clockKeeper mqtt:readingTopic ?stream ; mqtt:onBus ?anyBus ;
                           sensing:senseMode ?senseMode }}
  # Whether THIS CHANNEL is watched for crossings (#151) — per sensor, not per board,
  # because which values a board can watch is a hardware fact per channel: a ULP reaches the
  # analog probe and never the DHT. The board wakes for any watched channel that crosses.
  OPTIONAL {{ ?sensor ssn:implements sensing:CrossingProcedure . BIND(true AS ?crossing) }}
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
  OPTIONAL {{ ?sensor sensing:samples ?sample }}
  OPTIONAL {{ ?sensor mqtt:onBus ?bus }}
  OPTIONAL {{ ?sensor mqtt:readingTopic ?readingTopic }}
  OPTIONAL {{ ?sensor mqtt:readingPointer ?readingPointer }}
  OPTIONAL {{ ?sensor mqtt:commandTopic ?commandTopic }}
  # Through the stream it publishes on, because an encoding is the stream's — see
  # knowledge/decisions/a-stream-is-a-thing.md. Both halves are derived; this query runs over
  # the whole store at boot rather than over `$given`, so it may read a conclusion.
  OPTIONAL {{ ?sensor mqtt:publishesOn ?readingChannel . ?readingChannel codec:decodedBy ?decodedBy }}
  OPTIONAL {{ ?sensor scaling:scaledBy ?scaledBy }}
  OPTIONAL {{ ?sensor scaling:quantityUnit ?quantityUnit }}
 }}"""


def _actuators_q(agent_uri: str) -> str:
    return f"""
SELECT ?actuator ?localId ?subject ?subjectId ?commandTopic ?mlPerSecond ?maxDoseMl ?statusTopic
WHERE {{
  <{agent_uri}> actuation:hasActuator ?actuator .
  ?actuator ag:localId ?localId ; actuation:actuates ?subject ; mqtt:commandTopic ?commandTopic ;
            actuation:mlPerSecond ?mlPerSecond ; actuation:maxDoseMl ?maxDoseMl .
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
  OPTIONAL {{ ?sensor sensing:samples ?sample }}
  OPTIONAL {{ ?actuator mqtt:statusTopic ?statusTopic }}
 }}"""


def _markets_q(agent_uri: str, relation: str) -> str:
    return f"""
SELECT ?market ?localId ?resource ?offerTopic ?bidTopic ?claimTopic ?redeemTopic ?capacity
WHERE {{ 
  <{agent_uri}> market:{relation} ?market .
  ?market ag:localId ?localId ; market:marketFor ?resource ;
          market:offerTopic ?offerTopic ; market:bidTopic ?bidTopic ; market:claimTopic ?claimTopic .
  OPTIONAL {{ ?market market:redeemTopic ?redeemTopic }}
  OPTIONAL {{ ?resource market:lotCapacity ?capacity }}
 }}"""


# Everyone entitled to bid here — the host needs this to know who may answer an offer.
def _participants_q(market_uri: str) -> str:
    return f"""
SELECT ?agentId WHERE {{ 
  ?agent market:bidsIn <{market_uri}> ; ag:localId ?agentId  }}"""


def _market_from(row: dict) -> Market:
    return Market(
        uri=row["market"], local_id=row["localId"], resource=row["resource"],
        offer_topic=row["offerTopic"], bid_topic=row["bidTopic"],
        claim_topic=row["claimTopic"], redeem_topic=row.get("redeemTopic"),
        capacity_l=float(row["capacity"]) if row.get("capacity") else 0.0,
    )


def load_world(query: QueryFn) -> World:
    """The shared, public part: the version.

    A `subject_physics` dict used to be loaded here too — every plant's dry rate and
    litres-per-fraction, read through the WATER DOMAIN'S OWN TERMS from the kernel, and
    consumed by nothing at all: the simulator gets its physics through the generated model,
    and a bidder's conversion is its own belief. Dead code and a domain leak in one, which is
    the usual pairing (#148) — a fact nobody reads is a fact nobody notices the kernel had no
    business naming.
    """
    rows = bindings(query(_VERSION_Q))
    if not rows:
        raise WorldError("no ag:World with a current version — has the world been seeded?")
    return World(version=int(rows[0]["v"]))


def load_self(query: QueryFn, agent_id: str) -> Self:
    """Everything the world says about ME. The starting point of every agent process."""
    rows = bindings(query(_self_q(agent_id)))
    if not rows:
        raise WorldError(
            f"the world knows no agent with localId {agent_id!r} — "
            "check AGORA_AGENT_ID against the world it was given"
        )

    first = rows[0]
    me = Self(
        uri=first["agent"],
        agent_id=agent_id,
        capabilities=frozenset(r["capability"] for r in rows),
        acts_for=first.get("actsFor"),
        acts_for_id=first.get("actsForId"),
        event_topic=first.get("eventTopic"),
    )

    me.sensors = tuple(
        Sensor(
            uri=r["sensor"], local_id=r["localId"], subject=r["subject"],
            subject_id=r.get("subjectId") or "", observes=r["observes"],
            sense_mode=r.get("senseMode"),
            sample=r.get("sample"),
            crossing=bool(r.get("crossing")),
            bus=r.get("bus"), reading_topic=r.get("readingTopic"),
            reading_pointer=r.get("readingPointer"),
            command_topic=r.get("commandTopic"),
            decoded_by=r.get("decodedBy"), scaled_by=r.get("scaledBy"),
            quantity_unit=r.get("quantityUnit"),
        )
        for r in bindings(query(_sensors_q(me.uri)))
    )
    me.actuators = tuple(
        Actuator(
            uri=r["actuator"], local_id=r["localId"], subject=r["subject"],
            subject_id=r.get("subjectId") or "", command_topic=r["commandTopic"],
            ml_per_second=float(r["mlPerSecond"]), max_dose_ml=float(r["maxDoseMl"]),
            status_topic=r.get("statusTopic"),
        )
        for r in bindings(query(_actuators_q(me.uri)))
    )
    me.markets = tuple(_market_from(r) for r in bindings(query(_markets_q(me.uri, "bidsIn"))))
    me.hosted_markets = tuple(
        _market_from(r) for r in bindings(query(_markets_q(me.uri, "hosts")))
    )
    return me


def load_bus(query: QueryFn) -> MessageBus:
    """Where the society meets. The one piece of infrastructure that is a belief, not an
    environment variable — because everyone must agree on it."""
    rows = bindings(query(_BUS_Q))
    if not rows:
        raise WorldError("the world declares no mqtt:MessageBus — has it been seeded?")
    if len(rows) > 1:
        # A second bus is meaningful, but then resources must say which one they are on
        # (mqtt:onBus) and this becomes a lookup. Refuse to guess.
        raise WorldError(f"{len(rows)} buses declared; mqtt:onBus routing is not implemented")
    row = rows[0]
    return MessageBus(uri=row["bus"], host=row["host"], port=int(row["port"]),
                      tls_port=int(row["tlsPort"]) if row.get("tlsPort") else None)


def participants(query: QueryFn, market: Market) -> frozenset[str]:
    """Who may bid here. Public — a host must know who its counterparties are."""
    return frozenset(r["agentId"] for r in bindings(query(_participants_q(market.uri))))

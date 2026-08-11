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
    # WHO HOLDS THE CLOCK — ag:Scheduled keeps an interval it is given, ag:Push keeps its own.
    # The derivation already reads this to decide whether the agent gains ag:Subscribing or
    # ag:Listening; carrying it here is what lets the runtime partition what the derivation
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


@dataclass(frozen=True)
class Market:
    """A venue and its three channels."""

    uri: str
    local_id: str
    resource: str  # URI of what is allocated
    offer_topic: str
    bid_topic: str
    voucher_topic: str
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
    subject_physics: dict[str, dict] = field(default_factory=dict)  # subject id -> facts


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
       ?readingPointer ?commandTopic ?decodedBy ?scaledBy ?quantityUnit
WHERE {{
  <{agent_uri}> ag:polls ?sensor .
  ?sensor ag:localId ?localId ; ag:monitors ?subject ; sosa:observes ?observes .
  OPTIONAL {{ ?sensor ag:senseMode ?senseMode }}
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
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
SELECT ?actuator ?localId ?subject ?subjectId ?commandTopic ?mlPerSecond ?maxDoseMl
WHERE {{ 
  <{agent_uri}> actuation:hasActuator ?actuator .
  ?actuator ag:localId ?localId ; actuation:actuates ?subject ; mqtt:commandTopic ?commandTopic ;
            actuation:mlPerSecond ?mlPerSecond ; actuation:maxDoseMl ?maxDoseMl .
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
 }}"""


def _markets_q(agent_uri: str, relation: str) -> str:
    return f"""
SELECT ?market ?localId ?resource ?offerTopic ?bidTopic ?voucherTopic ?capacity
WHERE {{ 
  <{agent_uri}> market:{relation} ?market .
  ?market ag:localId ?localId ; market:marketFor ?resource ;
          market:offerTopic ?offerTopic ; market:bidTopic ?bidTopic ; market:voucherTopic ?voucherTopic .
  OPTIONAL {{ ?resource ag:capacityL ?capacity }}
 }}"""


# Physical facts about the subjects — public, because it is how the world behaves.
_PHYSICS_Q = f"""
SELECT ?subject ?subjectId ?dryRate ?litresPerFraction WHERE {{ 
  ?subject ag:localId ?subjectId .
  OPTIONAL {{ ?subject ag:dryRatePerTick ?dryRate }}
  OPTIONAL {{ ?subject ag:litresPerFraction ?litresPerFraction }}
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
        voucher_topic=row["voucherTopic"],
        capacity_l=float(row["capacity"]) if row.get("capacity") else 0.0,
    )


def load_world(query: QueryFn) -> World:
    """The shared, public part: the version and the physics of the subjects."""
    rows = bindings(query(_VERSION_Q))
    if not rows:
        raise WorldError("no ag:World with a current version — has the world been seeded?")
    world = World(version=int(rows[0]["v"]))
    for row in bindings(query(_PHYSICS_Q)):
        world.subject_physics[row["subjectId"]] = {
            "uri": row["subject"],
            "dry_rate": float(row["dryRate"]) if row.get("dryRate") else None,
            "litres_per_fraction": (
                float(row["litresPerFraction"]) if row.get("litresPerFraction") else None
            ),
        }
    return world


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

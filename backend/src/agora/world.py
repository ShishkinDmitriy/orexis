"""The world — public topology and composed capabilities. Everything is found, nothing named.

An agent process is handed exactly one instance identifier: its own id. From that it reads
this graph and learns what it *is* — what it acts for, what it may poll, which market it
belongs to, what it can do — and where every one of those things lives on the wire.

Two rules hold throughout this module:

- **Discovery by term, never by name.** The world is found by `?w a ag:World`, the market by
  `ag:bidsIn`, the supplier by whoever hosts. No query mentions an instance.
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
class Sensor:
    """A device an agent may poll, and where to reach it."""

    uri: str
    local_id: str
    subject: str  # URI of what it monitors
    subject_id: str
    observes: str  # URI of the property it reads
    reading_topic: str
    command_topic: str


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


_VERSION_Q = f"""
SELECT ?v WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?world a ag:World ; ag:currentVersion/ag:versionNumber ?v }} }} LIMIT 1"""


def _self_q(agent_id: str) -> str:
    """Find me by my id — the only instance identifier the process is given."""
    return f"""
SELECT ?agent ?capability ?actsFor ?actsForId ?eventTopic WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?agent a ag:Agent ; ag:localId "{agent_id}" ; ag:hasCapability ?capability .
  OPTIONAL {{ ?agent ag:actsFor ?actsFor . OPTIONAL {{ ?actsFor ag:localId ?actsForId }} }}
  OPTIONAL {{ ?agent ag:eventTopic ?eventTopic }}
}} }}"""


def _sensors_q(agent_uri: str) -> str:
    return f"""
SELECT ?sensor ?localId ?subject ?subjectId ?observes ?readingTopic ?commandTopic
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  <{agent_uri}> ag:polls ?sensor .
  ?sensor ag:localId ?localId ; ag:monitors ?subject ; sosa:observes ?observes ;
          ag:readingTopic ?readingTopic ; ag:commandTopic ?commandTopic .
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
}} }}"""


def _actuators_q(agent_uri: str) -> str:
    return f"""
SELECT ?actuator ?localId ?subject ?subjectId ?commandTopic ?mlPerSecond ?maxDoseMl
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  <{agent_uri}> ag:hasActuator ?actuator .
  ?actuator ag:localId ?localId ; ag:actuates ?subject ; ag:commandTopic ?commandTopic ;
            ag:mlPerSecond ?mlPerSecond ; ag:maxDoseMl ?maxDoseMl .
  OPTIONAL {{ ?subject ag:localId ?subjectId }}
}} }}"""


def _markets_q(agent_uri: str, relation: str) -> str:
    return f"""
SELECT ?market ?localId ?resource ?offerTopic ?bidTopic ?voucherTopic ?capacity
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  <{agent_uri}> ag:{relation} ?market .
  ?market ag:localId ?localId ; ag:marketFor ?resource ;
          ag:offerTopic ?offerTopic ; ag:bidTopic ?bidTopic ; ag:voucherTopic ?voucherTopic .
  OPTIONAL {{ ?resource ag:capacityL ?capacity }}
}} }}"""


# Physical facts about the subjects — public, because it is how the world behaves.
_PHYSICS_Q = f"""
SELECT ?subject ?subjectId ?dryRate ?litresPerFraction WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?subject ag:localId ?subjectId .
  OPTIONAL {{ ?subject ag:dryRatePerTick ?dryRate }}
  OPTIONAL {{ ?subject ag:litresPerFraction ?litresPerFraction }}
}} }}"""

# Everyone entitled to bid here — the host needs this to know who may answer an offer.
def _participants_q(market_uri: str) -> str:
    return f"""
SELECT ?agentId WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?agent ag:bidsIn <{market_uri}> ; ag:localId ?agentId }} }}"""


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
            "check AGORA_AGENT_ID against genesis/world.ttl"
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
            reading_topic=r["readingTopic"], command_topic=r["commandTopic"],
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


def participants(query: QueryFn, market: Market) -> frozenset[str]:
    """Who may bid here. Public — a host must know who its counterparties are."""
    return frozenset(r["agentId"] for r in bindings(query(_participants_q(market.uri))))

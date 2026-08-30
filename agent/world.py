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

from orexis_progression_patience.ontology import WORLD_GRAPH
from orexis_progression_patience.store import QueryFn, bindings


class WorldError(RuntimeError):
    """The world does not say something the code needs. Genesis is wrong, not the runtime."""


#  `MessageBus` and `load_bus` WERE HERE — the kernel asking the world for `mqtt:MessageBus`
#  and its ports, the last package word it spoke. Where a society meets is the transport's to
#  find, in its own vocabulary: the transport's module — a capability the fact of the bus grants — finds it, and
#  `packages/orexis-transport-mqtt/module.py` answers (the-kernel-has-no-mailbox).

#  `Sensor`, `Actuator` and `Market` WERE HERE, and `load_self` loaded all three by their
#  packages' words — the kernel knowing what a probe, a valve and a venue are, in SPARQL the
#  ratchet could not see (self-is-bdi-and-wiring-is-the-packages). Each lives in its package's
#  `wiring.py` now, loaded by the module that owns it, and `Self` is what an agent IS.


@dataclass
class Self:
    """What an agent IS, from the world's point of view: its own row, and no one else's.

    Its id, its capabilities, and whom it acts for — BDI's structure and nothing a package
    owns. What it is WIRED TO — sensors, actuators, venues — is each package's to load
    (`sensing.wiring`, `actuation.wiring`, `market.wiring`), because a kernel that loads
    packages should know no probe, no valve and no venue.
    """

    uri: str
    agent_id: str
    capabilities: frozenset[str]
    acts_for: str | None = None  # URI of the subject it advances
    acts_for_id: str | None = None

    def can(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass
class World:
    version: int


_VERSION_Q = f"""
SELECT ?v WHERE {{ 
  ?world a ag:World ; ag:currentVersion/ag:versionNumber ?v  }} LIMIT 1"""


def _self_q(agent_id: str) -> str:
    """Find me by my id — the only instance identifier the process is given."""
    return f"""
SELECT ?agent ?capability ?actsFor ?actsForId WHERE {{ 
  ?agent a ag:Agent ; ag:localId "{agent_id}" ; ag:hasCapability ?capability .
  OPTIONAL {{ ?agent ag:actsFor ?actsFor . OPTIONAL {{ ?actsFor ag:localId ?actsForId }} }}
 }}"""


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
            "check OREXIS_AGENT_ID against the world it was given"
        )

    #  MORE THAN ONE MATCH IS NOT A CHOICE TO MAKE. Rows come one per (agent x capability), so
    #  two agents sharing an id would be silently unioned here — the first one's node and
    #  subject, holding both agents' capabilities, reporting nothing wrong. `orexis-validate`
    #  refuses such a world (`ids_are_unique`); this is the same refusal at the other end, for
    #  a volume built before that check existed or a world amended past it.
    nodes = {r["agent"] for r in rows}
    if len(nodes) > 1:
        raise WorldError(
            f"{len(nodes)} agents answer to localId {agent_id!r} — {', '.join(sorted(nodes))}. "
            "An id names a broker principal, a bucket and this agent's own graphs, so there is "
            "no safe way to pick one; fix the world and re-run orexis-validate."
        )

    first = rows[0]
    return Self(
        uri=first["agent"],
        agent_id=agent_id,
        capabilities=frozenset(r["capability"] for r in rows),
        acts_for=first.get("actsFor"),
        acts_for_id=first.get("actsForId"),
    )



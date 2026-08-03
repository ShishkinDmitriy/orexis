---
type: Decision
title: World graph — public topology, private everything-else
description: All configuration moves into the belief base, split by kind: the world holds only the wiring (public, versioned, stated once); limits, cadence, desire and prices are each agent's private opinion. No config file remains.
status: accepted
stage: v1
tags: [belief-base, topology, genesis, config, privacy, ontology]
timestamp: 2026-08-02T00:00:00Z
---

# Context

Configuration lived in `backend/config/plants.yaml`: targets, bands, cadence, prices, tank
capacity, valve calibration, all in one file the code read at startup. That file was a second
source of truth sitting *next to* the belief base, and it flattened a distinction the rest of
the architecture takes seriously — it stated "fern's target is 0.55" and "fern draws from
barrel1" in the same voice, as if both were the same kind of fact.

They are not. One is **wiring** (public, shared, checkable — everyone must agree fern's
sensor is fern's sensor). The other is **opinion** (private, divergent, revisable — what fern
*wants* is nobody else's business, and another agent for the same plant could reasonably want
something else).

# Decision

**There is no config file.** Everything an agent needs is in the belief base, split by kind:

| | `:world` | `:beliefs/<agent>` |
|---|---|---|
| **holds** | topology + physical facts | desire, limits, cadence, valuation |
| **visible to** | everyone | that agent only |
| **authored by** | the sovereign, at genesis | the agent (seeded at genesis) |
| **versioned** | yes (`agora:versionNumber`) | no — it changes as the agent learns |
| **kind of claim** | fact | opinion |

The world graph exists **so the wiring is stated once** instead of being repeated inside every
agent's beliefs — that is its whole job. It is deliberately thin:

```turtle
ag:fern_agent a ag:Agent ; ag:localId "fern" ;
    ag:actsFor ag:fern ; ag:polls ag:moisture_sensor_fern ; ag:bidsIn ag:barrel1_market .
ag:moisture_sensor_fern a ag:Sensor ; ag:monitors ag:fern ; ag:senseMode ag:Pull .
ag:valve_fern a ag:Valve ; ag:actuates ag:fern ; ag:mlPerSecond 10.0 .
ag:supplier a ag:Agent ; ag:hasActuator ag:valve_fern , … .
```

and each agent's own graph carries what it thinks:

```turtle
ag:fern_agent ag:hasTarget 0.55 ; ag:bandLow 0.35 ; ag:bandHigh 0.65 ;
    ag:fastSleepS 30 ; ag:slowSleepS 600 ; ag:maxReadingAgeS 120 ;
    ag:litresPerFraction 2.0 ; ag:maxValuePerL 0.80 .
```

# Agent, Sensor, Actuator become first-class

The T-Box gains `ag:Agent`, `ag:Sensor` (`sosa:Sensor`), `ag:Actuator`/`ag:Valve`
(`sosa:Actuator`), and the connection properties `actsFor` / `polls` / `hasActuator` /
`monitors` / `actuates`. (These were first drafted as `agentFor`/`hasSensor`; the later split
into capability modules renamed them to the transport-neutral forms used above. See
[capability-modules](/decisions/capability-modules.md).) Two consequences worth naming:

**An agent is no longer a plant.** `Plant` used to be a subclass of `Agent`, so `agora:fern`
was both the thing measured and the thing bidding. Now `agora:fern` is a
`sosa:FeatureOfInterest` with no stake, and `agora:fern_agent` acts *for* it. Observations are
about the plant; wallets and bids belong to the agent. The conflation was harmless while each
plant had exactly one agent, and would have become confusing the moment it didn't.

**`polls` IS the access grant.** The capability from
[trusted-agent-mode](/decisions/trusted-agent-mode.md) stops being a separate mechanism and
becomes topology: fern's agent is wired to fern's sensor and to no other, and it subscribes
per-sensor rather than to a wildcard, so the isolation is visible in the code rather than
asserted in a comment.

# Startup is a belief-base read

An agent boots by reading the world (*what am I connected to?*), then its own beliefs (*what
do I want, and how closely should I watch?*), and starts polling. Nothing is passed in.
That is the whole configuration story now.

# Where each old config key went

- targets, bands, cadence, freshness, value model → `:beliefs/<agent>` (opinion)
- supplier's quantity, reserve, round cooldown → `:beliefs/supplier` (its terms are its own)
- valve calibration (`mlPerSecond`, `maxDoseMl`) → the **valve** in `:world` — a physical fact
  about that hardware, so the executor reads dosing from the device
- barrel capacity → the **source** in `:world`; it is the constitution's allocation ceiling
- drying rate + litres-per-fraction → the **plant** in `:world` (physics)
- `executor.actuate`, simulator tick → **environment variables**; these are deployment
  toggles, not beliefs anyone holds
- the **message broker** → the world, as an `ag:MessageBus`. It started in `.env` and moved:
  a channel name is meaningless without the broker it is on, and members who disagree about
  the bus are not one society. What is left in the environment is the bootstrap pair — which
  agent this process is, and where the belief base lives — plus deployment toggles.

# The same term in two graphs, meaning two different things

`agora:litresPerFraction` appears on a *plant* in `:world` (how much water that pot actually
takes) and on an *agent* in its beliefs (how much it **believes** its pot takes — which is
what its bid is computed from). They coincide today. An agent that learns would revise its own
copy, and being wrong about it would cost it money. Modelling the belief separately from the
fact is what makes that possible later; the un-domained property is deliberate.

# Genesis authors Turtle directly

`plants.yaml` is deleted. The sovereign hand-writes `genesis/world.ttl` and
`genesis/beliefs-<agent>.ttl` in the same vocabulary the agents read, and `agora-seed` PUTs
each file into its graph. One language end to end, no YAML→RDF translation layer to drift.
The genesis *process* is unchanged (see [genesis](/decisions/genesis.md)) — narrate, draft,
ratify, write — only the ratified artifact's format changed.

# Consequences

- **SHACL now checks the constitution, not just the record.** Because limits are triples, the
  shapes can enforce that a band is actually a band (`bandLow sh:lessThan bandHigh`), that an
  agent watches *more* closely when thirsty (`fastSleepS sh:lessThanOrEquals slowSleepS`), and
  that nobody sleeps past the cadence ceiling (`sh:maxInclusive 900`). `agora-validate` is now
  a genuine constitutional check, and the shipped `genesis/` is validated in CI-able tests.
- **Re-genesis replaces editing.** Changing the wiring means editing `world.ttl` and bumping
  `versionNumber`; every fact recorded afterwards is stamped with it.
- **Read authorization is now enforced**, which this decision only set up: per-agent store
  credentials and a per-graph access list generated from this graph, so `:beliefs/fern` is
  private in fact and not only by habit. Writes remain unscoped — the same gap
  [trusted-agent-mode](/decisions/trusted-agent-mode.md) accepts. See
  [belief-base-isolation](/decisions/belief-base-isolation.md).
- **Seam kept open:** the world is versioned but not yet *amendable at runtime* — agents read
  it once at startup. A world-version bump should eventually be an event agents react to.

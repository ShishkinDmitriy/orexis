---
type: Decision
title: Capability modules — code reads terms, never instances
description: A capability is an ontology module + SHACL rules + derivation rules + a code module. Capabilities are derived at genesis from hardware and wiring; an agent process is given only its own id and discovers everything else.
status: accepted
stage: v1
tags: [ontology, modules, capabilities, genesis, architecture, agents]
timestamp: 2026-08-03T00:00:00Z
---

# Context

Configuration had already moved into the belief base (see
[world-graph](/decisions/world-graph.md)), but the *code* was still full of the world:
`"sensors/{id}/moisture"` built from a naming convention, `supplier_id = "supplier"`,
`ag:world` as a well-known IRI, cadence bounds as Python constants, numeric fallbacks
whenever a term was missing. And a single process loaded every agent, which meant the round
was computed by reading everybody's private valuation — the thing the whole design forbids.

# Decision — one rule, applied everywhere

**Code may reference T-Box terms. Code may never reference an instance.**

A class, a property, a capability — these are public, well-known, and a program is written
against them exactly as it is written against a function signature. An *instance* — a name, a
topic, an id, a number — is discovered from the graph. The single exception is the identifier
a process is handed at boot: **its own agent id**. Everything else follows from that.

# A capability is four files

| | |
|---|---|
| `ontology/<name>.ttl` | the vocabulary — what this capability's terms mean |
| `shapes/<name>.ttl` | the rules — what an agent must believe to hold it |
| `rules/<name>.ru` | the derivation — what wiring gives an agent this capability |
| `backend/src/agora/modules/<name>.py` | the code — which reads only that vocabulary |

The modules are `core`, `transport`, `polling`, `market`, `actuation`, and the domain plug-in
`water`. Adding a capability — forecasting, say — touches none of the existing ones: write
the four files, add one line of registry, and no agent has it until genesis derives it.

# Capabilities are derived from hardware, not declared

The sovereign never writes down what an agent can do — only what exists and what is wired to
what. `rules/*.ru` then computes ability from connection:

- wired to a **pull-mode** sensor → `ag:Polling`: the agent owns a cadence;
- wired to a **push-mode** sensor → `ag:Listening`: it records what arrives, and is never
  asked for a cadence, because it has no way to apply one;
- plumbed into a market → `ag:Bidding`; owning the venue → `ag:Hosting`;
- holding actuators → `ag:Actuation`.

This is the load-bearing part. A declaration can drift from reality; a derivation cannot.
Reflash a board from push to pull, re-run genesis, and the agent gains a cadence with no edit
to the agent at all. And because the shapes are keyed to the derived capability, *what an
agent is required to believe follows from its hardware too* — a listening agent that stated a
cadence would fail validation, because that cadence would be a fiction.

The rules read across two graphs deliberately: the **world** says what type a device is, the
**T-Box** says what that type is a kind of. So a rule written against `ag:Actuator` picks up
an `ag:Valve` without naming it, and a new kind of actuator works the day its class exists.

# One process per agent

`AGORA_AGENT_ID=fern agora-agent`. The process reads the world (*what am I?*), its own beliefs
(*what do I want?*), and loads exactly the modules its capabilities name. Nothing in it can
reach another agent's graph.

This forced the auction to become a **protocol**. The host cannot compute a bid — the
valuation is private and lives in another process — so a round is a conversation:

```
participant announces its own verdict (voluntary disclosure, not its raw state)
    -> host announces an offer with a deadline        [ag:offerTopic]
    -> each bidder looks at its own sensor and answers  [ag:bidTopic/<agent>]
    -> host matches, clearing validates, vouchers return [ag:voucherTopic/<agent>]
    -> the owner redeems them against its own hardware
```

`auction.py`, `clearing.py`, `market.py` are untouched and still pure; only the choreography
is new. Note what the host now sees: a bid and a band, never a moisture reading. Minimal
disclosure stopped being a policy and became a consequence of the process boundary.

A bidder **looks before it bids**: it asks its sensor and waits for that answer, rather than
nudging and then reading whatever was already stored — which would be bidding on the past
while claiming to have just looked. If the reading does not arrive before the round closes, it
misses the round. That is the honest outcome.

# No defaults

A missing belief is a startup error naming the term and the graph, not a silent fallback. A
fallback is a policy decision made in code — exactly what this removes — and it hides a
genesis error until the moment it matters. The shapes make the failure unreachable in a
validated world, so the check is a backstop rather than a burden.

# Consequences

- **`agora-validate` became a real constitutional check.** Bands must be bands, cadence must
  watch more closely when thirsty, nobody may sleep past the ceiling, every device must state
  where it is reachable — and each rule applies only to the agents it concerns.
- **Deployment is one unit per agent.** More units, but a crashed fern cannot take tomato with
  it, and the process boundary is what enforces privacy.
- **The domain is genuinely a plug-in.** `water.ttl` holds Plant, SoilMoisture, targets and
  bands; everything above it is domain-neutral.

# What is still open

- **Balances are self-reported.** The host takes the bidder's word for its wallet because the
  clearing-authored ledger does not exist yet (see
  [agent-centric-epistemics](/decisions/agent-centric-epistemics.md) §4). This is the honest
  stand-in, recorded rather than hidden — it is the one place the round trusts a self-report.
- **Graph privacy is convention.** No agent's code reads another's graph, but the triplestore
  would serve it to anyone who asked. Real isolation needs per-graph access control.
- **Capabilities are read once at boot.** A world-version bump should eventually be an event
  agents react to, rather than something they notice on restart.
- **Derivation is materialised, not maintained.** Rules run at genesis and write triples into
  the world; removing a wire does not retract the capability until the world is re-seeded.

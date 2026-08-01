---
type: Index
title: Domain
description: Index of domain concepts and components — the shared contract and invariants.
tags: [index, domain]
timestamp: 2026-08-01T00:00:00Z
---

# Domain

The shared contract — what each component is, what it's responsible for, and its
invariants. This is the layer agents read for context (in an LLM-heavy design, from the
T-Box). It describes the design; it is NOT the live sensed state.

# Agents (the only tier that negotiates)

* [agent](/domain/agent.md) - The general principal: certified identity, wallet, stake — the only tier the trust boundary constrains. Plant agent and supplier specialize it.
* [plant-agent](/domain/plant-agent.md) - A self-interested plant: desire, wallet, event-driven state machine, one LLM call for its stance.

# Trusted infrastructure (stake-free)

* [gateway](/domain/gateway.md) - Sole author of attested beliefs; sensor/forecast → Influx + `:attested`; the one threshold authority.
* [clearing](/domain/clearing.md) - Standalone stake-free function that matches bids/asks and computes the allocation.
* [executor](/domain/executor.md) - The trusted actuator: validates the capability grant and drives the pump/valve. The only thing that touches hardware.
* [supplier](/domain/supplier.md) - Strategic seller that hosts the auction (calls clearing) and, in v2, buys upstream.

# Rules and resources

* [constitution](/domain/constitution.md) - Hard, non-negotiable constraints enforced by code, not persuasion.
* [round](/domain/round.md) - The iterative auction round: how a situation opens, iterates, and clears.
* [wallet](/domain/wallet.md) - The single budget; how bids and metabolic cost are computed and debited.
* [belief-base](/domain/belief-base.md) - Named-graph layout, SOSA shape, provenance, the two-store split.

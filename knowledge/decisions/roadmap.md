---
type: Decision
title: Staging roadmap — v1 scope and what the seams unlock
description: What to build now, what's parked, and which decision opens each extension.
status: accepted
stage: v1
tags: [roadmap, scope]
timestamp: 2026-08-01T00:00:00Z
---

# v1 — build this now

Three plant agents (Fern, Tomato, Succulent), one strategic supplier hosting one iterative
auction, grounded in real sensors on a Raspberry Pi.

Components: [gateway](/domain/gateway.md) → [belief base](/domain/belief-base.md) →
[clearing](/domain/clearing.md) inside the [supplier](/domain/supplier.md) →
[plant agents](/domain/plant-agent.md). Build order: gateway first (most settled, most
trusted), then clearing (pure code, fully unit-testable with scripted bids), then agents
(the only LLM part, stubbed against a working clearing).

Supplier cost is a **fixed constant** with a reserve price. See [strategic-supplier](/decisions/strategic-supplier.md).

# Parked, with the seam that unlocks each

- **Nested markets** (supplier is a buyer upstream; scarcity propagates down as price) —
  unlocked by [strategic-supplier](/decisions/strategic-supplier.md) leaving cost as a
  replaceable input. (v2)
- **Multi-source / N-to-N** (many suppliers, reverse auctions, exchange) — unlocked by
  [standalone-clearing](/decisions/standalone-clearing.md) + [bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md). (v2/v3)
- **Decentralized decomposition** (local auctions coupled by price, no global view) —
  the real thesis; sequential decomposition is the honest stepping-stone. (v3)
- **Self-organization** (elected/rotating chair, borrowed or spawned mediator) — chair gets
  procedural authority only; the privileged powers never transfer to a borrowed chair (see
  [trust-boundary](/decisions/trust-boundary.md) / [thin-trusted-infra](/decisions/thin-trusted-infra.md)). (v2)
- **Sybil / open-system** (naturalize + endow, currency minted not seized, reputation on
  identity). (v2)
- **World genesis tool** (sovereign narrates → LLM drafts topology + charters → ratify →
  infra writes; versioned, amendable migrations) — unlocked by [genesis](/decisions/genesis.md);
  v1 hand-authors the ratified config. (v2/v3)
- **Futures market** (a distinct venue from the v1 **spot** auction): win **held claims**,
  redeemable until `exp`; the agent **spends** them to actuate on its own schedule — win and
  actuate *decoupled*. Enables temporal strategy (water at night, wait for rain, hedge a
  forecast). Adds a claim inventory, a supplier redemption ledger, and forward-vs-option
  reservation. Unlocked by the claim's `exp` seam
  ([authn-authz-capabilities](/decisions/authn-authz-capabilities.md)). (v2/v3)
- **Domain-as-plugin** (swap ontology → electricity instead of plants) — unlocked by
  [llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) (agents read the T-Box
  from context). Extract seams from watering *first*, don't abstract prematurely. (v3)

- **Enforced bus privacy — DONE**, by
  [series-and-bus-isolation](/decisions/series-and-bus-isolation.md). Per-agent broker
  credentials and topic ACLs derived from the wiring, plus a per-agent Influx bucket, so an
  agent can no longer watch its neighbours' readings on the wire *or* read their history. What
  remains of this item is **TLS**: credentials authenticate, they do not encrypt, so anything
  with a port mirror still sees every payload. That is the last precondition for taking the
  society adversarial — a signing sensor stops an agent authoring its own readings, isolation
  stops it reading others' minds, and encryption stops it listening.

- **BDI completed: the gap, the aim, the intention, the deliberator** — the four phases of
  [an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md),
  tracked as #119 → #120 → #121 → #122 — **DONE**, all four. What remains open is exactly the
  seam the phases were run to create: `deliberation:Consulting`, the LLM member, declared and
  unimplemented, its constraints already fixed in the vocabulary. That member is the "only LLM
  part" v1 promises, made affordable by intentions persisting between calls.

# Working principle

Extract-from-concrete. Build watering concretely; keep the four seams visible (value model,
constitution, ontology, clearing) but don't generalize until a second domain pushes on them.

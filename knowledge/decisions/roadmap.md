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
  procedural authority only; mint/actuate/attest stay in permanent infrastructure. (v2)
- **Sybil / open-system** (naturalize + endow, currency minted not seized, reputation on
  identity). (v2)
- **World genesis tool** (sovereign narrates → LLM drafts topology + charters → ratify →
  infra writes; versioned, amendable migrations) — unlocked by [genesis](/decisions/genesis.md);
  v1 hand-authors the ratified config. (v2/v3)
- **Futures market** (a distinct venue from the v1 **spot** auction): win **held vouchers**,
  redeemable until `exp`; the agent **spends** them to actuate on its own schedule — win and
  actuate *decoupled*. Enables temporal strategy (water at night, wait for rain, hedge a
  forecast). Adds a voucher inventory, a supplier redemption ledger, and forward-vs-option
  reservation. Unlocked by the voucher's `exp` seam
  ([authn-authz-capabilities](/decisions/authn-authz-capabilities.md)). (v2/v3)
- **Domain-as-plugin** (swap ontology → electricity instead of plants) — unlocked by
  [llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) (agents read the T-Box
  from context). Extract seams from watering *first*, don't abstract prematurely. (v3)

# Working principle

Extract-from-concrete. Build watering concretely; keep the four seams visible (value model,
constitution, ontology, clearing) but don't generalize until a second domain pushes on them.

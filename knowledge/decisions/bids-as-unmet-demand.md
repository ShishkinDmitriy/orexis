---
type: Decision
title: Bids are a function of unmet demand
description: An agent bids for what it still needs, updated by prior allocations.
status: accepted
stage: v1
tags: [seam, economy, decomposition]
timestamp: 2026-08-01T00:00:00Z
---

# Context

N-to-N can be decomposed into local auctions, but **naive parallel** clearing double-counts
demand: an agent bidding in two auctions to hedge can win both and be over-served while
another starves. The fix is to reconcile through *state* (sequential, decrement satisfied
demand between auctions) or *price* (iterative coupling).

# Decision

Make each agent's bid a **pure function of its current *unmet* need**, updated by whatever
it has already been allocated. See [plant-agent](/domain/plant-agent.md) and [wallet](/domain/wallet.md).

# Why (the seam)

In v1 there's one auction, so this is trivially satisfied. But if v1 hardcodes "bid for full
target regardless of prior allocation," multi-source decomposition in v2 breaks. Writing bids
as unmet-demand keeps both sequential and price-coupled decomposition open for free.

# Related

- [standalone-clearing](/decisions/standalone-clearing.md) - the other seam that makes
  multi-source markets a caller change.
- [roadmap](/decisions/roadmap.md) - where decomposition lands (v2/v3).

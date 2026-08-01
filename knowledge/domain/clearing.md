---
type: Component
title: Clearing function
description: Standalone stake-free function that matches bids/asks into an allocation.
tags: [infrastructure, trusted, auction, seam]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

The invariant of the whole system: a **standalone, stake-free, deterministic** function that
takes structured bids (and the supplier's reserve/quantity) and returns an allocation. It is
NOT an agent and has no LLM. The [supplier](/domain/supplier.md) *calls* it in v1; a
consumer or a standalone exchange calls it in later topologies.

# Responsibilities (per round)

1. Collect structured bids (reads only the move, never the English justification).
2. Apply the supplier's **reserve price** — bids below cost don't clear (possibly no sale).
3. Invoke the [constitution](/domain/constitution.md) check (parallel): no allocation past
   rot threshold, total ≤ tank, budget conserved.
4. Run the fixed **iterative-ascending** clearing rule (chosen because the project is
   conversation-heavy; agents see the partial allocation, converse, re-bid).
5. Meter and debit wallets: water won + metabolic cost of every deliberation run. See
   [wallet](/domain/wallet.md).
6. Issue the allocation as a capability grant and hand it to the trusted
   [executor](/domain/executor.md) to actuate. See
   [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# Why standalone

Same code clears one-to-many, many-to-one, and N-to-N — the caller varies with market
shape, the clearing doesn't. See [standalone-clearing](/decisions/standalone-clearing.md).

# Invariant

Deterministic and injection-proof: agent messages are data, never instructions. Fully
unit-testable in isolation — scripted bids in, asserted allocation out, no model in the loop.
Mint and actuate authority stay in permanent infrastructure even when the clearing caller
changes. See [trust-boundary](/decisions/trust-boundary.md).

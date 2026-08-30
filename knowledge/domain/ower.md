---
type: Service
title: Ower
description: >-
  The service that keeps what this agent owes — one row per claim the society issued against it,
  with the counterparty, the amount and the window. It is the only writer of the obligations
  graph, and its rows become obligations the search ranges over rather than facts anyone may retract.
---

# What it runs

**Debt keeping.** `owe` raises a row when a claim is issued; `demanded` marks it presented;
`discharge` closes it. Each row is an [obligation](/domain/obligation.md) — a want this agent did
not source — so a debt is pursued through the same road as anything else it wants.

# What it reads and writes

![ower — what it reads and writes](../diagrams/service-ower.svg)

**Durable on purpose.** A host's in-memory record of what it issued dies with the process; the
ledger is what survives a restart, which is why a claim raises a row whether or not the holder
ever presents it.

# What it is not

**Not the market's**, though everything that *causes* a debt is: `hosting` is the only caller of
`owe`, `demanded` and `discharge`. What makes it the kernel's is the other side — an
[obligation](/domain/obligation.md) is a desire someone else sourced, so the
[deducer](/domain/deducer.md) builds a want from this ledger and the [planner](/domain/planner.md)
ranks that want beside everything else the agent pursues. Move it into the market package and
`agent/planner.py` would import one, which rule 2 forbids and `lint-imports` refuses.

An agent with no stake of its own still keeps this ledger, which is why it is the kernel's and
not a grant.

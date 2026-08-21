---
type: Decision
title: The scarce side hosts; clearing is topology-invariant
description: Who runs the auction rotates with market shape; the clearing validator does not.
status: accepted
timestamp: 2026-08-01T00:00:00Z
---

# Context

"Who hosts the auction" is relative to market shape: the **scarce (short) side hosts** — the
side there is not enough of, around which the many cluster (the micro short-side principle).
The host rotates; the thing that must stay invariant is clearing.

# Decision

Keep **clearing off the host** and make it a thin, stake-free **validator** (see
[clearing-as-validator](/decisions/clearing-as-validator.md)). The host *runs the auction*
and proposes a match; clearing *checks and co-signs* it. Because clearing validates rather
than allocates, it is **topology-invariant** — it does not know or care who hosted.

# Why (the seam)

The host is the only thing that changes across topologies:
- 1 supplier, N consumers → the [supplier](/domain/supplier.md) hosts (forward auction) — v1
- N suppliers, 1 consumer → the consumer hosts (reverse auction)
- N ↔ N → no participant can host. This row first read "a stake-free exchange hosts (order
  book)"; that resolution was refused when the case was decided — N-to-N clears through
  dealers holding stock, or bilaterally where too thin. See
  [the-market-has-no-governor](/decisions/the-market-has-no-governor.md), which also states
  what "scarce side" means precisely: the *structurally* short side, never the side deficit
  makes eager today — state opens rounds, structure names the host.

In every case the participants sign their **orders** (bids or asks), the host signs the
**match**, and clearing signs the **validation** — the same predicate over signed orders. So
a new topology is a change of *host*, not a rewrite of clearing. Mint and actuate stay in
infrastructure regardless of host. See [roadmap](/decisions/roadmap.md) and
[clearing](/domain/clearing.md).

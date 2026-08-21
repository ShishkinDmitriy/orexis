---
type: Decision
title: Strategic supplier (Design B)
description: The supplier is a real seller with costs and a reserve price, not a neutral utility.
status: accepted
timestamp: 2026-08-01T00:00:00Z
---

# Context

Two framings for the water source: (A) a stake-free utility that just dispenses, or (B) a
genuine seller with its own costs (electricity, pump wear, upstream water price) that it
wants to cover plus a margin.

# Decision

Choose **Design B — a strategic supplier**. It has a cost and sets a **reserve price**;
plant bids below cost don't clear (sometimes *no plant gets water*). Its strategy lives in
the reserve and release quantity.

# The safety line (critical)

A seller that also *judges its own auction* will rig it. The resolution is not to stop the
supplier running the auction, but to stop it *cheating*: it may run the auction and propose
the match, but [clearing](/domain/clearing.md) **validates** that trade (conservation,
solvency, identity, constitution, order-consistency) and co-signs it before settlement.
Greedy terms are fine; a trade that breaks an invariant is rejected. Seller runs the
auction; neutral clearing checks nobody cheated. See
[clearing-as-validator](/decisions/clearing-as-validator.md).

# Seam for v2

The supplier reasons about "my cost". In v1 that cost is a **fixed constant** (e.g. €0.20/L
upstream). In v2 it's replaced by a real upstream market where the supplier is a *buyer* —
the same node is seller downstream, buyer upstream. See [roadmap](/decisions/roadmap.md).
Leave the cost as a clearly-marked input so the upstream market can replace it.

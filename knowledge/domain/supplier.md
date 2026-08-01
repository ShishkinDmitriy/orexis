---
type: Domain Concept
title: Supplier
description: Strategic seller that hosts the auction and (v2) buys water upstream.
tags: [agent, market, supplier, seam]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

The water source as a **strategic seller** (Design B): it has real costs (electricity, pump
wear, upstream water price) and wants to cover them plus a margin. It is the organizing
nucleus — consumers cluster around the resource, and scarcity makes the auction emerge.

# Role is scoped

- **Downstream (to plants): seller / host.** Sets a **reserve price** and release quantity
  strategically, then a committed [clearing](/domain/clearing.md) rule awards. Its *strategy*
  is the terms; its *integrity* is the committed rule — it never peeks at bids and re-decides.
- **Upstream (v2, to its source): buyer / participant.** Just another bidder in *that*
  market. Same node, two positions. Markets couple only through **price**, never shared control.

# Responsibilities (v1)

1. Announce available water for the round (opens via a [round](/domain/round.md)).
2. Compute a reserve price from cost. In **v1 the cost is a fixed constant** (e.g. €0.20/L);
   leave it as a clearly-marked replaceable input. See [strategic-supplier](/decisions/strategic-supplier.md).
3. Call the standalone [clearing](/domain/clearing.md) function.

# Seam

v2 replaces the constant cost with an actual upstream auction the supplier bids in; scarcity
then propagates down the chain as price. See [roadmap](/decisions/roadmap.md).

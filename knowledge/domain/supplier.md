---
type: Domain Concept
title: Supplier
description: Strategic seller that hosts the auction and (v2) buys water upstream.
tags: [agent, market, supplier, seam]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

The water source as a **strategic seller** (Design B): it has real costs (electricity, pump
wear, upstream water price) and wants to cover them plus a margin. In v1 it is the **host**
of the auction — but only because it is the *scarce side* (supply is the bottleneck;
consumers cluster around it). Hosting is not intrinsic to being a supplier; it belongs to
whichever side is short. Money is the *medium*, not the good: money-scarcity gates who can
bid, it does not select the host. How the auction forms, who's in the cluster, and how
consumers and suppliers know each other (the attested plumbing topology) is in
[market](/domain/market.md). See [standalone-clearing](/decisions/standalone-clearing.md).

# Host role is scoped — it runs the auction, not the clearing

- **Downstream (to plants): seller / host.** It sets a **reserve price** and release quantity
  strategically, runs the auction, and proposes a match — signing it (`match_sig`). Its
  *strategy* is the terms; it may be as greedy as its scarcity allows. What it cannot do is
  cheat: [clearing](/domain/clearing.md) validates the proposed trade (conservation,
  solvency, identity, constitution, order-consistency) and **co-signs** it before settlement.
  Greedy-but-checked, not trusted-to-be-fair. See
  [clearing-as-validator](/decisions/clearing-as-validator.md).
- **Upstream (v2, to its source): buyer / participant.** Just another bidder in *that*
  market. Same node, two positions. Markets couple only through **price**, never shared control.

# Responsibilities (v1)

1. Announce available water for the round (opens via a [round](/domain/round.md)).
2. Compute a reserve price from cost. In **v1 the cost is a fixed constant** (e.g. €0.20/L);
   leave it as a clearly-marked replaceable input. See [strategic-supplier](/decisions/strategic-supplier.md).
3. Run the auction, collect the participants' signed bids, and propose the match.
4. Submit the proposed trade to [clearing](/domain/clearing.md) for validation (co-signature,
   or public-function recomputation — see [thin-trusted-infra](/decisions/thin-trusted-infra.md)).
5. **Actuate** — as the resource owner, drive its own valves to fulfil each voucher: *how
   much* from the voucher, *which valve* from its **actuator map**. It executes, it does not
   decide; bounded by the cleared voucher and the device fail-safe. This is the "executor"
   role, hosted by the supplier. See [executor](/domain/executor.md).

The supplier owns **one valve per plant it serves** — a genesis-configured `{plant_id →
valve}` map (its own infrastructure, part of the attested topology). It knows the winning
*agent*, not a valve; the voucher's **plant ID indexes the map** to select the valve. In v1
this is the plant-keyed MQTT topic `actuators/<plant>/valve`; a direct-GPIO supplier holds a
`{plant_id → pin}` map instead.

Mint is *not* the supplier's: [clearing](/domain/clearing.md) debits wallets; the supplier
gets paid but cannot create currency. See [thin-trusted-infra](/decisions/thin-trusted-infra.md).

# Seam

v2 replaces the constant cost with an actual upstream auction the supplier bids in; scarcity
then propagates down the chain as price. See [roadmap](/decisions/roadmap.md).

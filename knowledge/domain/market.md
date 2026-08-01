---
type: Domain Concept
title: Market (formation & membership)
description: How an auction condenses out of scarcity, who hosts, who's in the cluster, and how participants find each other.
tags: [market, auction, topology, discovery, emergence]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

A market is **not a standing thing** — it *condenses out of scarcity* and dissolves again.
There is no permanent "the auction"; there are momentary [rounds](/domain/round.md) that
form when a resource becomes contested and clear away when it doesn't.

# When it opens — condenses out of scarcity

No scarcity, no auction. If supply ≥ demand, the [supplier](/domain/supplier.md) just
**dispenses** (subject to the [constitution](/domain/constitution.md)). A round opens only
when **demand exceeds available supply at/above the reserve** — the resource becomes
*contested*. The trigger is always the same event, *excess demand crosses above zero*, moved
by one of four shocks:

- **Demand shock** — a consumer crosses into need (a plant hits `:LOW`).
- **Supply shock** — available quantity changes (refill / delivery); triggers *only if*
  demand still exceeds the new amount, else it is merely dispensed.
- **Budget shock** — the allowance is minted; previously-**broke** agents can now bid, so
  latent demand activates. See [wallet](/domain/wallet.md).
- **Belief shock** — an attested belief shifts valuations (rain forecast attested → re-bid).

# Who hosts — the scarce side of the *good*

The scarce (short) side of the **good** hosts (short-side principle): v1 = the supplier
(supply-scarce); a consumer in a buyer's market (reverse auction). See
[standalone-clearing](/decisions/standalone-clearing.md). **Money is the *medium*, not the
good**: money-scarcity **gates participation** (can this agent afford to bid?) — it does not
select the host. A round simply *waits* for the allowance, then a budget shock opens it,
still hosted by the water-scarce supplier.

# Who initiates — an agent, never infra

The [gateway](/domain/gateway.md) never initiates; it publishes attested percepts (the
environment's sensory surface). A consumer observes *its own* attested moisture cross `:LOW`
and **proactively** signals need; the host **proactively** convenes. Both are agents acting;
infra only updated the record.

# The cluster — ephemeral, emergent, per-round

The cluster crystallizes per round around the scarce nucleus and dissolves after. Members are
whoever, at that instant, is both **relevant** (unmet demand — or supply, on the sell side)
and **able** (solvent + certified). Membership is **dynamic across rounds** — join when
thirsty-and-solvent, leave when satisfied or broke — and new agents can be naturalized and
endowed (v2). Durable *membership* (the cert) is separate from ephemeral *participation*
(answering this round's call with a valid order); presence is emergent from the bus, not a
registry. See [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# How participants know each other — three kinds of knowing

With several markets (supply-A and its consumers, supply-B and its consumers), clusters are
delineated **not by discovery but by structure**:

- **Who is legitimate** → **certificates** (identity). Signed orders name a certified id.
- **Who is in my market** → the **attested topology** — the plumbing/reachability graph in
  the belief base (which plants share which tank: `plant :servedBy :tankA`,
  `:tankA :suppliedBy :supplierA`). This is *structural attested truth*, sovereign-declared
  at setup (like the [charter](/domain/agent.md)); agents **read but never rewire** it (trust
  boundary). A supplier convening a round addresses its cluster = the consumers plumbed to
  it; a consumer knows its supplier(s) = its taps. See
  [two-store-beliefs](/decisions/two-store-beliefs.md) and [belief-base](/domain/belief-base.md).
- **Who is here right now** → emergent from the **MQTT bus**, scoped by a per-market topic —
  whoever answers the call with a signed order.

So a consumer does not *wander looking* for suppliers, and a supplier does not *discover* its
consumers ad hoc: the topology tells each of them, and the bus carries the conversation.

# Multi-source (the seam)

A consumer plumbed to *both* supplies is in *both* clusters — it bids in both auctions and
reconciles across them by [bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md)
(decrement satisfied demand), so it is not double-served. The two markets couple **only
through price** (a multi-homed consumer prefers the cheaper source; scarcity in one
propagates as price), never shared control. This is the N-to-N seam; v1 has one supply and
one cluster.

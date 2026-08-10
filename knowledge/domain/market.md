---
type: Domain Concept
title: Market (structure & membership)
description: A market is the standing structure — a resource, who can supply it, who can consume it, and the links between them. The auction is the process that condenses inside it and dissolves again.
tags: [market, auction, topology, discovery, emergence]
timestamp: 2026-08-01T00:00:00Z
---

# What it is — structure, not an event

A market is the **standing structure**: a resource, agents that can supply it, agents that can
consume it, and the links between them. It is in the world, it has a name and channels, and
participants discover it rather than being configured with it. `ag:Market` is exactly this.

**The auction is the process.** It condenses out of scarcity, allocates, and dissolves — see
[round](/domain/round.md), which is the unit it runs in. A market with nothing contested is
still a market; there is simply no auction happening in it.

This page said the opposite until recently — that a market "is not a standing thing" — while
`ag:Market` was declared in `world.ttl` with three MQTT topics on it. Both were called *market*
and they were opposites, which is worth recording rather than quietly fixing: the confusion sent
two separate design attempts to the wrong premise, because a fact about the venue and a fact
about the round genuinely belong in different places. **Structure is the market's; the terms of a
given auction are its host's** (see
[matching-is-a-capability](/decisions/matching-is-a-capability.md)). What an auction *is* is
[auction](/domain/auction.md).

# When an auction opens — it condenses out of scarcity

**The design**: no scarcity, no auction. If supply ≥ demand, the
[supplier](/domain/supplier.md) just **dispenses** (subject to the
[constitution](/domain/constitution.md)). A round opens only when **demand exceeds available
supply at/above the reserve** — the resource becomes *contested*. The trigger is always the same
event, *excess demand crosses above zero*, moved by one of four shocks:

- **Demand shock** — a consumer crosses into need (a plant hits `:LOW`).
- **Supply shock** — available quantity changes (refill / delivery); triggers *only if*
  demand still exceeds the new amount, else it is merely dispensed.
- **Budget shock** — the allowance is minted; previously-**broke** agents can now bid, so
  latent demand activates. See [wallet](/domain/wallet.md).
- **Belief shock** — an attested belief shifts valuations (rain forecast attested → re-bid).

**What is built** is the demand shock and nothing else, and it is a weaker trigger than the
above describes. A round opens when one agent announces `LOW` — a **band**, not a quantity —
and the host cannot compare demand to supply at that moment because demand is private until
bids are in. So "excess demand crosses above zero" is not what fires, and there is no dispense
path: every round competes on price, including the ones where nothing turned out to be scarce.
Why the host is deliberately blind to quantity beforehand, and what the gap costs, is in
[the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md).

# A market is a lot, not a property

`ag:marketFor` names a **resource** and nothing more. What is auctioned is a quantity of a
thing — 1L of water — and that is true whether or not anyone's soil is dry. Winning changes a
property; the auction is not *about* one.

This was briefly modelled the other way, with the resource's class stating which observable
property it relieved, so that a bidder could work out which of its readings to bid on. It reads
plausibly and it is wrong twice over: it makes a market undeclarable when it allocates something
no instrument measures — a time slot, a right of way, a share of attention — and it puts a fact
about the *bidder's* valuation on the *venue*, where every participant would have to agree to it.

The property-shaped thing is the **stake**. A target of 0.55 is 0.55 *of* something, and the
bands and `ag:litresPerFraction` are denominated in the same unit — `litresPerFraction` is
precisely the exchange rate between the lot and the property, which is where the coupling
honestly lives. So the domain states `ag:aboutProperty` on the desire term itself, the bidder
follows it from a term it already names, and the market stays a lot. See
[one-agent-many-sensors](../decisions/one-agent-many-sensors.md).

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

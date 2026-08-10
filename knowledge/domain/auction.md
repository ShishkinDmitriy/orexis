---
type: Domain Concept
title: Auction
description: The process, not a place. An auction condenses out of scarcity, collects bids over one or more rounds, allocates by matching, is co-signed by clearing, and dissolves. The market is the standing structure it happens inside; a round is one pass of bidding within it; who convenes it is stated in v1, not derived.
tags: [auction, market, process, protocol]
timestamp: 2026-08-10T00:00:00Z
---

# What it is — a process, not a thing

An **auction** is a **process**. It condenses out of scarcity, allocates a lot among the agents
that want it, and dissolves. Between auctions there is nothing left of it: no state, no object in
the world graph, no `ag:Auction` anywhere. What persists is the [market](/domain/market.md) — the
standing structure of a resource, who can supply it, who can consume it, and the channels they
meet on.

That distinction is load-bearing and the bundle had it backwards until recently. **Structure is
the market's; the terms of a given auction are its host's.** A market with nothing contested is
still a market; there is simply no auction happening in it. See
[bid-matching-is-a-capability](/decisions/bid-matching-is-a-capability.md), which had to fix the
vocabulary before it could say anything else.

# The four things it is made of

| | what it is | where it lives |
|---|---|---|
| [market](/domain/market.md) | the standing structure it happens inside | `market:Market` in the world |
| [round](/domain/round.md) | one pass of bidding inside it — exactly one is built | `capabilities/market/hosting.py` |
| [bid matching](/domain/bid-matching.md) | how a lot and the bids become an allocation with prices | `capabilities/market/matching.py` |
| [clearing](/domain/clearing.md) | the notary that validates and co-signs — never allocates | `agent/clearing.py` |

The line that holds them apart is **the host proposes, clearing disposes**. Matching decides
*who gets what and at what price*; clearing decides *whether that is permitted* — conservation,
solvency, identity, the [constitution](/domain/constitution.md) — and co-signs the
[voucher](/domain/voucher.md). Neither does the other's job, and an auction is the sequence in
which they take turns.

# Its life

1. **It condenses.** A participant announces it is in trouble — a **band**, `LOW`, its own
   judgement about its own sensed state — and the host convenes. Scarcity is the trigger, not a
   schedule and not an operator. A cooldown stops a flapping participant from spamming the
   market, and a host with an auction already open does not open a second.
2. **It announces its terms.** The offer carries the lot, the reserve, the deadline and
   `matches_by`. Terms travel with the invitation, because a bidder cannot bid well against terms
   it does not know.
3. **It collects bids.** Each bidder answers with a number only it can compute, from beliefs the
   host cannot see. Bids from agents that do not bid in that market are ignored; late bids and
   bids for another auction are dropped.
4. **It matches.** At the deadline the host asks whichever of its capabilities can match, and
   gets a proposed trade. See [bid matching](/domain/bid-matching.md).
5. **It is validated and settled.** [Clearing](/domain/clearing.md) checks the proposed trade and
   co-signs [vouchers](/domain/voucher.md); the [executor](/domain/executor.md) redeems them
   against the hardware.
6. **It dissolves.** The host's open-auction state is dropped, the cluster that crystallized
   around it disperses, and the market is exactly as it was.

Every step above is what runs today, and steps 1-3 are a single round. What
[round](/domain/round.md) describes beyond it — re-bidding after a shock, the LLM-phrased stance —
would be further rounds inside this same auction, and none of it is built.

# Who convenes it — stated in v1, not derived

The design is the **short-side principle**: the scarce side of the *good* hosts. With one
supplier and N thirsty consumers the [supplier](/domain/supplier.md) hosts a forward auction;
in a buyer's market a consumer would host a reverse one. Money-scarcity does not select the
host — money is the medium, not the good; it only gates who can afford to bid. That is what
[standalone-clearing](/decisions/standalone-clearing.md) and [market](/domain/market.md) record.

**Nothing implements it.** `market:hosts` is stated in `world.ttl`, and in every shipped world it
names the supplier statically. No code compares which side is short, and the host does not
rotate. The principle is a documented intention, and this page says so rather than describing it
as behaviour.

The split above sharpens the open question rather than resolving it: **owning the venue is
structural, convening an auction is per-auction.** So who convenes *this* auction could follow from
which side is short at that moment, while who owns the venue stays where it is. Nothing here
moves toward that.

And one route to it is closed rather than merely unbuilt. A rotating host looks like a job for a
**role** — an agent that *is* the host for the duration of one auction — but a role has to be a
role of something, and this page's own decision is that there is no auction object to be it of. See
[a-role-needs-something-to-be-a-role-in](/decisions/a-role-needs-something-to-be-a-role-in.md):
whether positions become roles and whether an auction becomes an object are the same question, and
the second is the one to argue.

# What an auction is not

- **Not a venue.** Discovery, membership and channels are the market's. An auction has no
  address.
- **Not the matching.** Propose, validate, issue is the auction's shape however the bids were
  matched — which is why `agent/auction.py` kept the sequence and lost the allocation.
- **Not a format.** *Auction format* names a bidding procedure and a payment rule together; this
  project models only the second, and [bid matching](/domain/bid-matching.md) says why and what the word
  costs when it is used loosely.
- **Not an object in the graph.** There is no `ag:Auction` to point at. Looking for one is the
  usual sign that a market fact and an auction fact have been confused.
- **Not a round.** A [round](/domain/round.md) is one pass of bidding *inside* an auction, which is
  the standard meaning and not what this page describes. Exactly one is built, so the two coincide
  today; see
  [a-round-is-an-iteration-not-the-auction](/decisions/a-round-is-an-iteration-not-the-auction.md).

---
type: Domain Concept
title: Auction
description: The process, not a place. An auction condenses out of scarcity, collects bids over one or more rounds, allocates by matching, is co-signed by clearing, and dissolves. The market is the standing structure it happens inside; a round is one pass of bidding within it; who convenes it is stated in v1, not derived.
---

# What it is — a process, not a thing

An **auction** is a **process**. It condenses out of scarcity, allocates a lot among the agents
that want it, and dissolves. Between auctions there is nothing left of it: no state, no object in
the world graph, no `ag:Auction` anywhere. What persists is the [market](/domain/market.md) — the
standing structure of a resource, who can supply it, who can consume it, and the channels they
meet on.

That distinction is load-bearing and the bundle had it backwards until recently. It is stated
where the standing thing is defined — see [market](/domain/market.md), *"structure, not an
event"* — and [bid-matching-is-a-capability](/decisions/bid-matching-is-a-capability.md) had to
fix the vocabulary before it could say anything else.

# The four things it is made of

| | what it is | where it lives |
|---|---|---|
| [market](/domain/market.md) | the standing structure it happens inside | `market:Market` in the world |
| [round](/domain/round.md) | one pass of bidding inside it — exactly one is built | `packages/capability/market/hosting.py` |
| [bid matching](/domain/bid-matching.md) | how a lot and the bids become an allocation with prices | `packages/capability/market/matching.py` |
| [clearing](/domain/clearing.md) | the notary that validates and co-signs — never allocates | `agent/clearing.py` |

The line that holds them apart is **the host proposes, clearing disposes**. Matching decides
*who gets what and at what price*; clearing decides *whether that is permitted* — conservation,
solvency, identity, the [constitution](/domain/constitution.md) — and co-signs the
[claim](/domain/claim.md). Neither does the other's job, and an auction is the sequence in
which they take turns.

# Its life

1. **It condenses.** A participant announces it is in trouble — a **band**, `LOW`, its own
   judgement about its own sensed state — and the host convenes. Scarcity is the trigger, not a
   schedule and not an operator. A cooldown stops a flapping participant from spamming the
   market, and a host with an auction already open does not open a second.
2. **It announces its terms.** The offer carries the lot, the reserve, the deadline and
   `matches_by`. Terms travel with the invitation rather than being discoverable, and
   [bid matching](/domain/bid-matching.md) says why that is a requirement and not a courtesy.
3. **It collects bids.** Each bidder answers with a number only it can compute, from beliefs the
   host cannot see. Bids from agents that do not bid in that market are ignored; late bids and
   bids for another auction are dropped.
4. **It matches.** At the deadline the host asks whichever of its capabilities can match, and
   gets a proposed trade. See [bid matching](/domain/bid-matching.md).
5. **It is validated and settled.** [Clearing](/domain/clearing.md) checks the proposed trade and
   co-signs [claims](/domain/claim.md); each winner presents its claim when its watch is
live (#132), and the [executor](/domain/executor.md) redeems the presented ones
   against the hardware.
6. **It dissolves.** The host's open-auction state is dropped, the cluster that crystallized
   around it disperses, and the market is exactly as it was.

Every step above is what runs today, and steps 1-3 are a single round. What
[round](/domain/round.md) describes beyond it — re-bidding after a shock, the LLM-phrased stance —
would be further rounds inside this same auction, and none of it is built.

# Who convenes it — derived from consent, settled as structure

`market:hosts` is DERIVED now, never stated: a source offered by someone who states
`market:matchesBy` IS a market, and the owner hosts it — one authored triple as consent,
everything else minted from the wiring
([a-market-arises-where-want-meets-supply](/decisions/a-market-arises-where-want-meets-supply.md)).
Both shipped venues arise this way: the supplier's for its barrel, the city's for its mains.

And "who rules" is settled, precisely
([the-market-has-no-governor](/decisions/the-market-has-no-governor.md)): rulership is
commitment power over the mechanism, which comes from STRUCTURE or neutrality and never from
today's deficit — state opens rounds, structure names the convener, and the *structurally*
short side is what the short-side principle always meant. At N-to-M no participant has
commitment power, and the refusal is recorded: no stake-free exchange — the market clears
through DEALERS holding stock (the shipped supplier is one) or bilaterally where too thin.
Money-scarcity still selects nothing, for the reason [market](/domain/market.md) gives under
*who hosts*.

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

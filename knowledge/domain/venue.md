---
type: Domain Concept
title: Venue
description: >-
  One market, as a node in the graph. MARKET is the standing structure in general; a venue is
  one of them — an instance of market:Market, minted at genesis from stock plus consent and
  keyed by its source, so one owner offering two goods holds two venues and each holds its
  paper for a time of its own. Not the auction, not the host, not the lot.
---

# What it is

A **venue** is one [market](/domain/market.md), as a node in the graph — `market:Market` is its
class, and the ontology's own section for that class is headed *the venue*. The two words carry
the two sides of one thing: *market* names the standing structure in general, and *venue* names
ONE of them — the shop an agent hosts, bids at, or holds a claim against. A sentence about "the
market" is a claim about the design; a sentence about "a venue" is about a node with an IRI,
which rule 1 forbids code to name and `?m a market:Market` to find.

# Minted from stock plus consent

Nobody authors a venue in the shipped worlds. Two facts that exist for their own reasons are
together the whole premise of a shop — a source `market:offeredBy` an owner, and that owner
stating `market:matchesBy` — and the derivation in `packages/capability/market/rules.ru` mints
the venue from exactly those. Consent alone opens it: a venue lacking its redeem window is
still derived and then refused loudly by its shape, rather than quietly missing from a world
that thought it had a market. The argument, and what hand-authoring one is still for — a world
may add a venue where the wiring implies none — is
[a-market-arises-where-want-meets-supply](/decisions/a-market-arises-where-want-meets-supply.md).

# Keyed by its source

A venue's identity is a function of its **source's** id, not its owner's. One owner offering
two goods therefore holds two venues, and each states terms of its own: `market:redeemWindowS`
is stated on the source and carried onto the venue minted from it, so the barrel's paper and
the mains' paper can be held for different lengths of time. The same key is what lets a
[dealer](/domain/dealer.md) face upstream and downstream at once — as two venues, not one
confused one.

# What a venue states

Everything an offer needs to be announced against it, and nothing about any participant:

- **how it matches** — `market:matchesBy`, the [bid matching](/domain/bid-matching.md) member
  in force, public before anyone bids;
- **its [good](/domain/good.md)** — reached as `marketFor/supplies` and deliberately never
  copied onto the venue as a triple of its own; what the good disambiguates is that page's;
- **its redeem window** — how long it holds what a winner won, and the fact that gives an
  [obligation](/domain/obligation.md) its urgency;
- **its channels** — the topics participants meet on, so a venue is discovered rather than
  configured.

What a venue must NOT state is any bidder's valuation; the model that put one there was
rejected, and [market](/domain/market.md) holds the argument.

# What it is not

- **Not the [auction](/domain/auction.md).** The auction is the event — it condenses inside a
  venue and dissolves, and the venue stands whether or not anything is contested.
- **Not the [host](/domain/host.md).** Hosting is a role an agent plays at a venue, and how
  owning one relates to convening auctions in it is that page's open question.
- **Not the [lot](/domain/lot.md).** The lot is the host's own belief about what to put up,
  offered at the venue rather than stated by it.

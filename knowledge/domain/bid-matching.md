---
type: Domain Concept
title: Bid matching
description: Turning a lot and a set of bids into a proposed allocation with prices — an allocation rule and a payment rule together. The host declares how it matches and the offer announces it; pay-as-bid and uniform price share the first and differ in the second, and each costs the bidder something different. Deliberately narrower than an auction format, and qualified because bare matching collides with matching a capability to a provider.
---

# What it is

**Bid matching** is the step that turns a lot and a set of bids into a **proposed allocation with
prices** — who gets how much, and what each of them pays. It is one input, one output, and no
conversation:

```
(offer, bids) -> trade
```

That is the whole contract. `agent/auction.py` names it `Match`, and every member of the family
satisfies it.

**Its two halves have standard names.** Mechanism design decomposes any mechanism into an
**allocation rule** — who gets what — and a **payment rule** — what each winner pays. A matching
member supplies *both*, and that is the exact statement of the width this word has to cover: the
family is not a pricing slot, and a member that priced without allocating would not satisfy
`Match`. (The auction literature often says *pricing rule* for the payment rule; this bundle says
payment rule throughout, because one word per concept is the point.)

Matching **proposes**; it never permits. Whether a proposed trade is well-formed, solvent and
constitutional is [clearing](/domain/clearing.md)'s, and clearing never allocates. *The host
proposes, clearing disposes* is the line, and matching is what the host does when it proposes.

# The word

**Bid matching** — and the qualifier is load-bearing, not decoration. Bare *matching* collides
inside this project: `agent.provider(family)` matches a request for an ability to whichever
module registered a member of it, so *matching capability* parses two ways. *Bid matching* says
which.

The qualifier is carried where something could be misread and nowhere else. `market:matchesBy`
has a host for its domain and this family for its range, so *supplier matchesBy PayAsBid* admits
one reading and stays as it is; so do `propose_match` and `Match`.

Why this word and not *rule* or *format* is argued in
[bid-matching-is-the-word](/decisions/bid-matching-is-the-word.md).

# What bid matching is NOT — the format it is only half of

In the literature an **auction format** (equivalently *auction type*) is a named combination of
two independent things:

1. **How bidding proceeds** — ascending open outcry (English), descending open outcry (Dutch),
   one-shot sealed bid, and so on.
2. **What the bidding produces** — the allocation rule and the payment rule together: first-price
   / discriminatory (each winner pays its own bid), uniform (every winner pays one clearing
   price), second-price, and so on.

**We model only the second.** `market:BidMatchingCapability` is the allocation-and-payment half alone.
The first axis is fixed here: [round](/domain/round.md) describes an iterative-ascending round,
and that is a property of the protocol in `packages/capability/market`, not a slot anything plugs into.

**Dutch makes it concrete.** A Dutch auction is descending open outcry — the auctioneer starts
high and lowers the price until someone accepts. It is a complete mechanism, fixing both axes.
But what makes it *Dutch* is the procedure; its payment rule is first-price, which is what we
call `market:PayAsBid`. The classic result sharpens it: **a Dutch auction is strategically equivalent
to a first-price sealed-bid auction** — in both, the moment you commit fixes your price, so a
bidder shades identically. Same payment rule, different procedure, same outcome.

| | bidding procedure | payment rule |
|---|---|---|
| Dutch | descending open | first-price *(= pay-as-bid)* |
| first-price sealed-bid | one-shot sealed | first-price *(= pay-as-bid)* |
| our round today | iterative ascending | `market:PayAsBid` or `market:UniformPrice` |

Dutch and sealed-bid differ on the left and agree on the right; our two differ on the right and
agree on the left. So Dutch is not a bid-matching capability and would not become one: if the bidding
procedure were ever made pluggable, Dutch would join *that* family and still match by pay-as-bid.

**And the term is worse than merely wide — it is ambiguous.** In finance, "Dutch auction" usually
means close to the opposite of the classic one: a sealed-bid **uniform-price** auction. Google's
IPO was described as a Dutch auction and was uniform-price sealed-bid; US Treasury auctions
attract the same label. The term means descending-open to an auction theorist and
uniform-price-sealed to a banker. When a term of art means two incompatible things depending on
who is speaking, a project has to define its own narrowly and say what it is not — which is
precisely why `matching` is our word and `format` is not.

# How a host says which one it runs

Bid matching is a **capability**, in the sense [capability-packages](/decisions/capability-packages.md)
gives the word: a family with interchangeable members, asked for by family and never by name.

- The host states `market:matchesBy market:PayAsBid` in the world. That is a fact about what it *does*.
- The capability `ag:hasCapability market:PayAsBid` is **derived** from it at genesis, never written
  by hand — the same as every other capability here.
- At runtime `hosting.py` asks `agent.provider(BID_MATCHING)` and gets whichever module registered
  that member. The market package does not know that pay-as-bid is implemented in Python at all.

It is the **host's** fact and not the market's, because an auction's terms belong to whoever
convenes it, and two hosts of one market could in principle run different auctions. A world that
states `market:matchesBy` on a non-host is refused by a shape; so is a host that states nothing.

**And it is public, announced in each offer.** `announce()` publishes `matches_by` alongside the
quantity, the reserve and the deadline, read off the provider rather than off a belief so that
what is advertised is necessarily what will run. A bidder cannot bid well against terms it does
not know: how much to shade is a direct function of which member is in force. Real auctions
announce their terms when they open, and so does this one. Nothing verifies the announcement —
see the seams in [bid-matching-is-a-capability](/decisions/bid-matching-is-a-capability.md).

# The two members, and what each costs you

Both are implemented, and in the decomposition above they **share an allocation rule and differ in
their payment rule**. Both walk the same demand curve — bids at or above the reserve, filled
highest-price-first, each capped by what is left — and disagree only about the bill. That is why
the walk is written out twice rather than factored into a shared helper: the agreement is a
property of *these two* members, not of the family, and a third that varied the allocation rule
instead — pro-rata, filling everyone who cleared the reserve in proportion to what they asked for —
is an ordinary member and would share nothing with them.

| | what a winner pays | what it rewards |
|---|---|---|
| `market:PayAsBid` | its own bid | **shading** — bid the least you think will win |
| `market:UniformPrice` | the lowest accepted bid | **demand reduction** — take less to keep the margin cheap |

- **Pay-as-bid** is discriminatory: a winner that bid well above the clearing point pays all of
  it. So the honest strategy is to shade, and the prices the host sees are not what anyone
  actually values.
- **Uniform price** pays everyone the marginal price — the lowest accepted bid, where the demand
  curve crossed the lot. Your own bid sets your bill only if you turn out to be marginal, so
  bidding true value is safe on *price*. The mirror weakness is on *quantity*: a bidder large
  enough to move the margin can ask for less in order to leave the margin at a cheaper bid, and
  pay less on everything it does take.

Neither is free. The trade is between misreporting what you value and misreporting how much you
want, and which is worse depends on how concentrated demand is. **Each member's `rdfs:comment`
states its own weakness**, and a new member that advertises only its strengths is worse than
none. Neither is strategy-proof, and no member here is: the mechanism that would be —
Vickrey-Clarke-Groves, pricing each winner at the externality it imposes — fits the same
signature and is not attempted.

# The uncontested round, under each member

`PayAsBidModule.propose_match` measures contest over the **eligible** bids — below-reserve
demand neither quiets a round nor profits from one — and when everything asked for fits inside
the lot, it fills everyone in full **at the reserve**. Under `UniformPrice` there is nothing to
detect: the clearing price *starts* at the reserve, so an uncontested round clears there by
construction.

So the two members still disagree exactly on the contested path, which is their reason to be
two, and switching a world between them remains one edit. Why pay-as-bid branches rather than
the world switching: [#50](https://github.com/ShishkinDmitriy/agora/issues/50) and
[uniform-price-dissolves-the-uncontested-round](/decisions/uniform-price-dissolves-the-uncontested-round.md).

# Where it lives

`packages/capability/market/`, in `market:`. `matching.py` holds both implementations; the family,
its members and `market:matchesBy` are declared in the package's `ontology.ttl`, the two shapes (a
host must say how it matches; only a host may) in its `shapes.ttl`, and the derivation is the third
update in its `rules.ru`. `agent/auction.py` holds the path around it: propose, validate, issue.

**It shares a package with the protocol and is still its own family.** A directory is a package,
not a capability — `packages/capability/market/` provides three. What keeps the two independent is
`PROVIDES` and the term, never the directory: `hosting.py` asks `agent.provider(BID_MATCHING)` and
never learns which member answered. See
[a-package-owns-its-namespace](/decisions/a-package-owns-its-namespace.md).

See [auction](/domain/auction.md) for the process matching is one step of,
[round](/domain/round.md) for the unit it runs in, and [clearing](/domain/clearing.md) for what
happens to its proposal next.

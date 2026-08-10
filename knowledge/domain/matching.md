---
type: Domain Concept
title: Matching
description: Turning a lot and a set of bids into a proposed allocation with prices. The host declares how it matches and the offer announces it; pay-as-bid and uniform price are implemented, and each costs the bidder something different. Matching is deliberately narrower than an auction format.
tags: [auction, matching, mechanism, ubiquitous-language]
timestamp: 2026-08-10T00:00:00Z
---

# What it is

**Matching** is the step that turns a lot and a set of bids into a **proposed allocation with
prices** — who gets how much, and what each of them pays. It is one input, one output, and no
conversation:

```
(offer, bids) -> trade
```

That is the whole contract. `agent/auction.py` names it `Match`, and every member of the family
satisfies it.

Matching **proposes**; it never permits. Whether a proposed trade is well-formed, solvent and
constitutional is [clearing](/domain/clearing.md)'s, and clearing never allocates. *The host
proposes, clearing disposes* is the line, and matching is what the host does when it proposes.

# The word

Three words were in circulation for this one thing — *matching*, *rule* and *format* — and all
three appeared in `hosting.py` alone. **Matching is the word.** It is accurate about the width of
what we model: it covers the allocation *and* the prices, and it survives a member that allocates
differently (pro-rata rather than highest-first), which is exactly the case the family exists to
allow.

*Rule* was the worst of the three, because `rules.ru` already means something specific in every
capability directory here — a SPARQL derivation. *Format* over-claims, for the reason the next
section gives. See [matching-is-the-word](/decisions/matching-is-the-word.md).

# What matching is NOT — the format it is only half of

In the literature an **auction format** (equivalently *auction type*) is a named combination of
two independent things:

1. **How bidding proceeds** — ascending open outcry (English), descending open outcry (Dutch),
   one-shot sealed bid, and so on.
2. **How the price is set** — first-price / discriminatory (each winner pays its own bid),
   uniform (every winner pays one clearing price), second-price, and so on.

**We model only the second.** `ag:MatchingCapability` is the pricing-and-allocation axis alone.
The first axis is fixed here: [round](/domain/round.md) describes an iterative-ascending round,
and that is a property of the protocol in `capabilities/market`, not a slot anything plugs into.

**Dutch makes it concrete.** A Dutch auction is descending open outcry — the auctioneer starts
high and lowers the price until someone accepts. It is a complete mechanism, fixing both axes.
But what makes it *Dutch* is the procedure; its pricing rule is first-price, which is what we
call `ag:PayAsBid`. The classic result sharpens it: **a Dutch auction is strategically equivalent
to a first-price sealed-bid auction** — in both, the moment you commit fixes your price, so a
bidder shades identically. Same pricing rule, different procedure, same outcome.

| | bidding procedure | pricing rule |
|---|---|---|
| Dutch | descending open | first-price *(= pay-as-bid)* |
| first-price sealed-bid | one-shot sealed | first-price *(= pay-as-bid)* |
| our round today | iterative ascending | `ag:PayAsBid` or `ag:UniformPrice` |

Dutch and sealed-bid differ on the left and agree on the right; our two differ on the right and
agree on the left. So Dutch is not a matching capability and would not become one: if the bidding
procedure were ever made pluggable, Dutch would join *that* family and still match by pay-as-bid.

**And the term is worse than merely wide — it is ambiguous.** In finance, "Dutch auction" usually
means close to the opposite of the classic one: a sealed-bid **uniform-price** auction. Google's
IPO was described as a Dutch auction and was uniform-price sealed-bid; US Treasury auctions
attract the same label. The term means descending-open to an auction theorist and
uniform-price-sealed to a banker. When a term of art means two incompatible things depending on
who is speaking, a project has to define its own narrowly and say what it is not — which is
precisely why `matching` is our word and `format` is not.

# How a host says which one it runs

Matching is a **capability**, in the sense [capability-packages](/decisions/capability-packages.md)
gives the word: a family with interchangeable members, asked for by family and never by name.

- The host states `ag:matchesBy ag:PayAsBid` in the world. That is a fact about what it *does*.
- The capability `ag:hasCapability ag:PayAsBid` is **derived** from it at genesis, never written
  by hand — the same as every other capability here.
- At runtime `hosting.py` asks `agent.provider(MATCHING)` and gets whichever module registered
  that member. The market package does not know that pay-as-bid is implemented in Python at all.

It is the **host's** fact and not the market's, because an auction's terms belong to whoever
convenes it, and two hosts of one market could in principle run different auctions. A world that
states `ag:matchesBy` on a non-host is refused by a shape; so is a host that states nothing.

**And it is public, announced in each offer.** `announce()` publishes `matches_by` alongside the
quantity, the reserve and the deadline, read off the provider rather than off a belief so that
what is advertised is necessarily what will run. A bidder cannot bid well against terms it does
not know: how much to shade is a direct function of which member is in force. Real auctions
announce their terms when they open, and so does this one. Nothing verifies the announcement —
see the seams in [matching-is-a-capability](/decisions/matching-is-a-capability.md).

# The two members, and what each costs you

Both are implemented. Both walk the same demand curve — bids at or above the reserve, filled
highest-price-first, each capped by what is left — and disagree only about the bill.

| | what a winner pays | what it rewards |
|---|---|---|
| `ag:PayAsBid` | its own bid | **shading** — bid the least you think will win |
| `ag:UniformPrice` | the lowest accepted bid | **demand reduction** — take less to keep the margin cheap |

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

# What closing #50 would take

[#50](https://github.com/ShishkinDmitriy/agora/issues/50) is the open defect that an
**uncontested** round is still priced as if contested: under pay-as-bid, a bidder with no rival
for anything still pays what it offered, charged for urgency that moved no allocation.

It is a defect *in pay-as-bid*, not in the auction. Two ways to close it, and choosing between
them is a governance call rather than a bug fix:

- **Branch inside pay-as-bid** — what the issue proposes: at `close()` the bids are in hand, so
  detect `sum(max_qty_l) <= quantity_l` and allocate everyone their full request at the reserve.
  A second code path, which has to be tested and must not become a way to pay less by bidding in
  a quiet round.
- **Switch the world to `ag:UniformPrice`** — one edit, `ag:matchesBy` on the supplier. There is
  then nothing to detect: the clearing price *starts* at the reserve and rises only if the walk
  exhausts the lot, so a round whose demand never reaches the lot clears at the reserve because
  nothing else could have happened.

**No world has switched.** All three still state `ag:matchesBy ag:PayAsBid`, deliberately —
changing it alters what every participant pays and how each should bid. See
[uniform-price-dissolves-the-uncontested-round](/decisions/uniform-price-dissolves-the-uncontested-round.md).

# Where it lives

`agent/capabilities/matching/` — `ontology.ttl` (the family and its members), `shapes.ttl` (a
host must say how it matches; only a host may), `rules.ru` (the derivation), `module.py` (both
implementations). `agent/auction.py` holds the path around it: propose, validate, issue.

See [auction](/domain/auction.md) for the process matching is one step of,
[round](/domain/round.md) for the unit it runs in, and [clearing](/domain/clearing.md) for what
happens to its proposal next.

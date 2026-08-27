---
type: Decision
title: Uniform price dissolves the uncontested round rather than branching on it
description: >-
  The second member of market:BidMatchingCapability, which both tests the family's claim that
  adding one moves nothing else and changes what issue #50 is. Under pay-as-bid an uncontested
  round needs a special case; under a uniform price with the reserve as its floor, a round
  whose demand never reaches the lot simply clears at the reserve — so #50 becomes a choice of
  mechanism rather than a defect to patch.
status: accepted
timestamp: 2026-08-10T00:00:00Z
---

# Context

[bid-matching-is-a-capability](bid-matching-is-a-capability.md) made matching a family,
`market:BidMatchingCapability`, with pay-as-bid implemented and `market:UniformPrice` declared beside it
under a claim: *"adding it is a class and one line of `PROVIDES`; no other package moves."*

A declared member with nothing behind it proves nothing. Two members do — and the claim was
falsifiable, which is most of why this was worth doing next.

# The claim held

Everything that changed is inside the matching package, plus tests. (It was its own directory at
the time — `capabilities/bid_matching/` — and is now `packages/orexis-capability-market/matching.py`; see
[a-package-owns-its-namespace](a-package-owns-its-namespace.md). The claim below is about what
did NOT have to move, and folding it in did not weaken that: `hosting.py` is still untouched.)

| | |
|---|---|
| `module.py` | `UniformPriceModule` added |
| `__init__.py` | one entry in `PROVIDES` |
| `ontology.ttl` | the member's comment stopped saying RESERVED |
| `terms.py` | a comment |

`hosting.py`, `auction.py`, the market package, the derivation rule and the shapes were not
touched. The derivation already granted whichever member a host named; the loader already
registered whichever module declared one; `agent.provider(BID_MATCHING)` already handed it over. A
world that says `market:matchesBy market:UniformPrice` now gets a host that runs it and announces it, and
nothing in between knew a second member was coming.

That is what a family is for, and it is now demonstrated rather than asserted.

# The mechanism, and the one convention that had to be settled

Allocation is identical to pay-as-bid — bids at or above the reserve, highest first, each capped
by what is left. Only the bill differs: **every winner pays the lowest accepted bid**, the one
that was still filling when supply ran out.

`market:UniformPrice`'s comment previously said *"the lowest accepted bid, or the highest rejected
one"*, which describes a family of conventions rather than naming one. Settled as **lowest
accepted**, for two reasons:

- With divisible quantities the marginal bidder is almost always *partially* filled, so its own
  price is simultaneously the lowest accepted and the highest rejected. The two can only differ
  where the lot happens to exhaust exactly on a bid boundary — a measure-zero case here.
- Lowest accepted needs nothing tracked about what was excluded, and it is what a treasury auction
  means by its stop-out price.

# Why this dissolves #50 instead of fixing it

[#50](https://github.com/ShishkinDmitriy/orexis/issues/50) records that an uncontested round is
priced as if contested: under pay-as-bid every winner pays its own bid, so a bidder with no rival
is charged for urgency that moved no allocation. Its proposed fix is a branch — detect
`sum(max_qty_l) <= quantity_l` at `close()`, and allocate at the reserve instead.

Under a uniform price there is nothing to detect. The clearing price **starts** at the reserve and
is only raised if the walk actually exhausts the lot:

```python
clearing = offer.reserve_price_per_l
for bid in eligible:
    ...
    if remaining <= EPS:
        clearing = bid.max_price_per_l
```

A round whose demand never reaches the lot is not a special case that was handled — it is a walk
that never crossed supply, so the price stays where the demand curve began. Everyone is filled and
everyone pays the reserve **because nothing else could have happened**.

The difference matters beyond elegance. A branch is a second path that has to be tested, and #50
itself warns of the failure mode: *"this must not become a way to pay less by bidding in a quiet
round."* With one code path there is no quiet-round path to game — a contested round clears at the
margin whatever anyone hoped.

# What each member costs you, which is what a sovereign is choosing between

Each member's `rdfs:comment` states its own weakness, and holding new ones to that is the standard
this family should keep. A member that advertises only its strengths is worse than none.

- **Pay-as-bid** rewards shading. A winner that bid well above the clearing point pays all of it,
  so the honest strategy is to bid the least you think will win — which means the prices the host
  sees are not what anyone actually values.
- **Uniform price** rewards demand reduction. Your bid sets your bill only if you turn out to be
  marginal, so bidding true value is safe on *price* — but a bidder large enough to move the
  margin can shade its **quantity**, taking less in order to leave the margin at a cheaper bid and
  pay less on everything it does take.

Neither is free. The trade is between misreporting what you value and misreporting how much you
want, and which is worse depends on how concentrated the demand is. In a society of three plants
where one is much thirstier than the others, demand reduction is the live risk.

# What is not decided here

**No world switched.** All three still state `market:matchesBy market:PayAsBid`, and every existing round
clears exactly as it did — `test_round.py` and the existing `test_auction.py` cases pass untouched,
which is the evidence that this added a member rather than changed one.

**#50 stayed open past this change**, deliberately: whether a world should run uniform price is
the sovereign's call, not this change's, since it alters what every participant pays and how
they should bid. *(Amended when #50 closed.)* The sovereign kept pay-as-bid and took the other
route — the explicit branch inside `PayAsBidModule.propose_match`, everyone filled at the
reserve when eligible demand fits the lot. The dissolution argument above is untouched: uniform
price still needs no such branch, and the branch pay-as-bid now carries is exactly the second
code path this record said it would be, held honest by the contested-path-unchanged test. The
two members now agree on the uncontested bill and differ on the contested one.

# Seams left open

- **Nothing selects between the two.** A world names one and gets it. With two implemented, the
  question [bid-matching-is-a-capability](bid-matching-is-a-capability.md) recorded is now live rather
  than hypothetical: nothing stops a world naming both, and nothing would choose.
- **The allocation walk is written out twice**, deliberately. That these two members allocate
  identically is a fact about them and not about the family — a pro-rata member across everyone
  who cleared the reserve is an ordinary answer and allocates differently. A helper factored out
  today would encode an invariant the family does not have; a test holds them to agreeing where they
  should.
- **Neither member is strategy-proof**, and none here could be. The mechanism that is —
  Vickrey-Clarke-Groves — prices each winner at the externality it imposes, which needs the
  allocation recomputed with that bidder absent. It fits the family's signature and nothing here
  attempts it.

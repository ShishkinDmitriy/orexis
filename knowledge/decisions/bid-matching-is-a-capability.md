---
type: Decision
title: Bid matching is a capability, and the host announces how it matches
description: Turning a lot and a set of bids into an allocation with prices left agent/auction.py and became market:BidMatchingCapability, with pay-as-bid implemented and uniform-price declared beside it. The host states how it matches, the capability is derived from that, and it travels in the offer — because a bidder cannot bid well against terms it does not know. Separating it first required separating market from auction, which the bundle had backwards.
status: accepted
stage: v1
tags: [market, auction, capabilities, protocol]
timestamp: 2026-08-10T00:00:00Z
---

This record was filed as *an-auction-format-is-a-capability* and retitled when the vocabulary was
settled: the thing described here is **matching**, and *auction format* means something wider that
this project does not model. Nothing else in it changed. See
[bid-matching-is-the-word](bid-matching-is-the-word.md) and [bid matching](/domain/bid-matching.md).

# Context

`agent/auction.py` said of itself that *"the auction format lives here (it's the host's strategy),
and it is a replaceable v1 choice"*, and `hosting.py` did `from agent.auction import run_round`.
Swapping greedy pay-as-bid for uniform-price meant editing that file. The seam was a claim.

A claimed seam is worse than an acknowledged gap because it is cited:
[the-lot-is-the-hosts-standing-offer](the-lot-is-the-hosts-standing-offer.md) and
[#50](https://github.com/ShishkinDmitriy/agora/issues/50) both park the pay-as-bid-versus-uniform-price
argument as *a separate argument*, on the assumption that there is somewhere to have it.

# First: a market is structure, an auction is a process

This could not be said cleanly until the vocabulary was fixed, because the bundle held both
readings of one word.

`domain/market.md` opened *"A market is **not a standing thing** — it condenses out of scarcity and
dissolves again. There is no permanent 'the auction'."* Meanwhile `market:Market` was declared in
`world.ttl` with three MQTT topics on it, and its own comment called it a *venue* that participants
*discover*. Both were called market and they are opposites.

The split, now stated in both places:

- **A market is the standing structure** — a resource, agents that can supply it, agents that can
  consume it, and the channels they meet on. It is in the world. A market with nothing contested
  is still a market.
- **An auction is the process** — it condenses out of scarcity, allocates, and dissolves. That is
  what [round](/domain/round.md) has always described.

The consequence that matters here: **the terms of an auction belong to whoever convenes it**, not
to the venue. A market that stated how bids are matched would be holding a fact nobody asked it to
keep, and could not express two hosts running different auctions in one market.

# Decision — matching is a capability, and the host states how it matches

`market:BidMatchingCapability` is the family. `market:PayAsBid` is implemented; `market:UniformPrice` is declared
beside it with no `PROVIDES` behind it, exactly as `perception:Polling` and `review:Consulting` are.

This is a capability by [AGENTS.md rule 2](../../AGENTS.md)'s test — the *how* could differ, and
visibly: under pay-as-bid a winner pays what it offered, so the honest strategy is to shade; under
a uniform price it pays the clearing price, so bidding true value costs nothing. **How a host
matches changes what a rational participant should say.** That is not a function.

The host states `market:matchesBy` and the capability is derived from it:

```sparql
?agent market:hosts ?market ; market:matchesBy ?matching .
?matching a market:BidMatchingCapability .
```

The stated fact is what the host *does*; the ability follows. So `world.ttl` still contains no
`ag:hasCapability`, and the prohibition is untouched.

## Named `matchesBy`, not `clearsBy`

Clearing is already a thing here — the validator that co-signs a trade, in
[clearing-as-validator](clearing-as-validator.md). Reusing the word would have made a host's
allocation read as the notary's business, which is precisely the boundary the phrase *the host
proposes, clearing disposes* exists to hold. A matching capability decides an allocation; whether
it is **permitted** is not its business and never was.

## Public, because a bid is an answer to terms

How a host matches is in the world, so every participant reads it. `auction.py` called it *the
host's strategy*, and a strategy is usually private — but this one is not strategy, it is the terms
of the game. Real auctions announce theirs; a sealed-bid first-price auction says so out loud. A
bidder that does not know whether it pays its own bid cannot compute what to offer, and a market
where that is hidden is not one anybody can bid in honestly.

## And announced per round, not just discoverable

`announce()` already published the quantity, the reserve and the deadline. The matching joins them:
**terms travel with the invitation.** Read off the provider rather than a belief, so what is
announced is necessarily what will run — a host cannot advertise one and apply another.

# Where the code went

- `propose_match` → `capabilities/market/matching.py`, as `market:PayAsBid`'s implementation. It is
  `@staticmethod`, because a lot and a set of bids fully determine the answer; a member that later
  needs the host's beliefs can stop being static then.
- `run_round` **stayed** in `agent/auction.py`. Propose, validate, issue is the auction's shape
  however the bids were matched — so under the vocabulary above, that file now holds exactly the
  auction and nothing of the matching. It takes `match` as a callable.
- `hosting.py` asks `agent.provider(BID_MATCHING)`, the same way `redeem` already asks for whoever can
  actuate. The market package no longer knows pay-as-bid is implemented in Python at all.

# Consequences

- **Adding uniform-price is a class and a line of `PROVIDES`.** No other package moves, which is
  the whole of what #66 asked for.
- **A host that says nothing about matching is refused before it runs.**
  `market:HostStatesHowItMatchesShape` catches it at validation; `close()` also refuses loudly,
  because a world can be amended after validation and losing a round's bids in silence is worse
  than saying so — every bidder is waiting on a voucher.
- **A world may state `market:UniformPrice` today** and derive a capability nothing provides. The agent
  reports it at startup, which is the honest failure and the same one `perception:Polling` produces.
- **#50 is unaffected and still open.** The uncontested-round defect is *in* pay-as-bid; this
  change gives it somewhere to be argued against, and deliberately did not touch the allocation.

# Seams left open

- **Who hosts.** [standalone-clearing](standalone-clearing.md) says the scarce side hosts and that
  the host rotates with topology; nothing implements it, and v1 declares the supplier statically.
  Under the split above the question sharpens rather than resolves: **hosting a market is
  structural, **convening an auction is per-auction**, so who convenes *this* auction could follow from
  which side is short at that moment. Nothing here moves toward it.
- **A market could be derived** rather than declared — agents that can supply a resource, agents
  that can consume it, and a link between them is the whole definition, and it is the same move
  capabilities already make. Not attempted.
- ~~**Nothing selects between two implementations.**~~ **Closed, by a shape rather than by a
  tie-break.** This seam anticipated that once `market:UniformPrice` was implemented a world stating
  both would need something to choose. It cannot: `market:matchesBy` carries `sh:maxCount 1`, so a host
  states exactly one member and there is no ambiguity to resolve. The question the seam was really
  reaching for survives as the one below it — not *which member* but *whether the one announced is
  the one that ran*. `review:Consulting` leaves the genuine version of this seam in
  [self-review-is-a-capability](self-review-is-a-capability.md), where the grant names a member
  directly and a second premise would be needed.
- **The offer announces the bid matching; nothing verifies it.** A bidder reads `matches_by` and
  trusts it. Clearing does not recompute the allocation — `validate` checks identity, no duplicate
  lines, each line within that buyer's own signed bid and at or above the reserve, conservation
  against the lot, solvency and the constitution. Every one of those still passes for a host that
  announces `market:UniformPrice` and then charges each winner its own bid, because each line is
  individually within its bidder's bid; the bidder shaded less because of what it was told, and
  pays for it. Under-allocating a rival is equally invisible. **This is the seam where bid matching
  would stop being the host's alone**: giving clearing the announced member and comparing turns the
  notary from a bounds-checker into a referee — and decides, as a side effect, whether clearing must
  see every bid. What would otherwise make it checkable is the same signing question left open
  elsewhere.

---
type: Decision
title: An auction format is a capability, and the host announces which one it runs
description: The allocation rule left agent/auction.py and became ag:MatchingCapability, with pay-as-bid implemented and uniform-price declared beside it. The host states the rule, the capability is derived from that, and the rule travels in the offer — because a bidder cannot bid well against terms it does not know. Separating it first required separating market from auction, which the bundle had backwards.
status: accepted
stage: v1
tags: [market, auction, capabilities, protocol]
timestamp: 2026-08-10T00:00:00Z
---

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
dissolves again. There is no permanent 'the auction'."* Meanwhile `ag:Market` was declared in
`world.ttl` with three MQTT topics on it, and its own comment called it a *venue* that participants
*discover*. Both were called market and they are opposites.

The split, now stated in both places:

- **A market is the standing structure** — a resource, agents that can supply it, agents that can
  consume it, and the channels they meet on. It is in the world. A market with nothing contested
  is still a market.
- **An auction is the process** — it condenses out of scarcity, allocates, and dissolves. That is
  what [round](/domain/round.md) has always described.

The consequence that matters here: **the terms of an auction belong to whoever convenes it**, not
to the venue. A market that stated the format would be holding a fact nobody asked it to keep, and
could not express two hosts running different auctions in one market.

# Decision — the rule is a capability, and the host states which one

`ag:MatchingCapability` is the family. `ag:PayAsBid` is implemented; `ag:UniformPrice` is declared
beside it with no `PROVIDES` behind it, exactly as `ag:Polling` and `ag:Consulting` are.

This is a capability by [AGENTS.md rule 2](../../AGENTS.md)'s test — the *how* could differ, and
visibly: under pay-as-bid a winner pays what it offered, so the honest strategy is to shade; under
a uniform price it pays the clearing price, so bidding true value costs nothing. **The rule changes
what a rational participant should say.** That is not a function.

The host states `ag:matchesBy` and the capability is derived from it:

```sparql
?agent ag:hosts ?market ; ag:matchesBy ?format .
?format a ag:MatchingCapability .
```

The stated fact is what the host *does*; the ability follows. So `world.ttl` still contains no
`ag:hasCapability`, and the prohibition is untouched.

## Named `matchesBy`, not `clearsBy`

Clearing is already a thing here — the validator that co-signs a trade, in
[clearing-as-validator](clearing-as-validator.md). Reusing the word would have made a host's
allocation rule read as the notary's business, which is precisely the boundary the phrase *the host
proposes, clearing disposes* exists to hold. A matching capability decides an allocation; whether
it is **permitted** is not its business and never was.

## Public, because a bid is an answer to terms

The format is in the world, so every participant reads it. `auction.py` called it *the host's
strategy*, and a strategy is usually private — but this one is not strategy, it is the rules of the
game. Real auctions announce their format; a sealed-bid first-price auction says so out loud. A
bidder that does not know whether it pays its own bid cannot compute what to offer, and a market
where that is hidden is not one anybody can bid in honestly.

## And announced per round, not just discoverable

`announce()` already published the quantity, the reserve and the deadline. The rule joins them:
**terms travel with the invitation.** Read off the provider rather than a belief, so what is
announced is necessarily what will run — a host cannot advertise one rule and apply another.

# Where the code went

- `propose_match` → `capabilities/matching/module.py`, as `ag:PayAsBid`'s implementation. It is
  `@staticmethod`, because a lot and a set of bids fully determine the answer; a rule that later
  needs the host's beliefs can stop being static then.
- `run_round` **stayed** in `agent/auction.py`. Propose, validate, issue is the auction's shape
  whichever rule allocated — so under the vocabulary above, that file now holds exactly the
  auction and nothing of the format. It takes `match` as a callable.
- `hosting.py` asks `agent.provider(MATCHING)`, the same way `redeem` already asks for whoever can
  actuate. The market package no longer knows pay-as-bid is implemented in Python at all.

# Consequences

- **Adding uniform-price is a class and a line of `PROVIDES`.** No other package moves, which is
  the whole of what #66 asked for.
- **A host with no rule is refused before it runs.** `ag:HostStatesItsRuleShape` catches it at
  validation; `close()` also refuses loudly, because a world can be amended after validation and
  losing a round's bids in silence is worse than saying so — every bidder is waiting on a voucher.
- **A world may state `ag:UniformPrice` today** and derive a capability nothing provides. The agent
  reports it at startup, which is the honest failure and the same one `ag:Polling` produces.
- **#50 is unaffected and still open.** The uncontested-round defect is *in* pay-as-bid; this
  change gives it somewhere to be argued against, and deliberately did not touch the allocation.

# Seams left open

- **Who hosts.** [standalone-clearing](standalone-clearing.md) says the scarce side hosts and that
  the host rotates with topology; nothing implements it, and v1 declares the supplier statically.
  Under the split above the question sharpens rather than resolves: **hosting a market is
  structural, hosting an auction is per-round**, so who convenes *this* round could follow from
  which side is short at that moment. Nothing here moves toward it.
- **A market could be derived** rather than declared — agents that can supply a resource, agents
  that can consume it, and a link between them is the whole definition, and it is the same move
  capabilities already make. Not attempted.
- **Nothing selects between two implementations.** With one member the question does not arise; the
  moment `ag:UniformPrice` is implemented, a world stating both would need a rule. The same seam
  `ag:Consulting` leaves in [self-review-is-a-capability](self-review-is-a-capability.md).
- **The offer announces the rule; nothing verifies it.** A bidder reads `matches_by` and trusts it.
  What would make that checkable is the same signing question left open elsewhere.

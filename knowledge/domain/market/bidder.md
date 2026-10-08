---
type: Role
title: Bidder
term: http://example.org/orexis/market#Bidder
description: >-
  An agent that bids in a venue - calls for a round, tenders into it, and presents the claim it
  wins. A role declared in the agent's own self graph and founded on the public relation
  `market:bidsIn`, which says where; beneath the planner, the executor, the speaker and the
  deliberator, which declaring it loads.
---

# What it is

`:rose_grower a orexis:Self , market:Bidder` in the grower's self graph, and
`:rose_grower market:bidsIn :water` in the society. The two are two facts with two readers: the role
says what the grower runs, and only the grower reads it; the relation says where it bids, and the
host's plans read it to know whom a round is told to.

What it does on the market is its own desire's to say — water when its soil reads dry — and the
[auction](/domain/market/auction.md)'s actions carry it out: a [call](/domain/market/call.md), a bid
into the [round](/domain/market/round.md), a [claim](/domain/market/claim.md) presented.

# What declaring it loads, and needs

For the reason the [host](/domain/market/host.md) gives, a bidder plans, walks, speaks and
deliberates too: the role sits beneath the same four package roles, and the boot loads belief,
planning, execution and speech for it. It needs a venue it bids in — the shape the market
ships beside the role asks for `market:bidsIn` — and `orexis-onboard` refuses a bidder bidding
nowhere ([role](/domain/kernel/role.md)).

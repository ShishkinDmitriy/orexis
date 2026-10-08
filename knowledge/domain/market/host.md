---
type: Role
title: Host
term: http://example.org/orexis/market#Host
description: >-
  The agent that holds a venue's good - it offers and clears the rounds and serves the claims. A
  role declared in the agent's own self graph and founded on the public relation `market:hosts`,
  which a world states and peers read; its two desires, no call unanswered and no presented claim
  unserved, are all it does on the market.
---

# What it is

`:supplier a orexis:Self , market:Host` in the supplier's self graph, and `:supplier market:hosts
:water` in the society. The role says what the supplier RUNS, and nothing but the supplier reads it;
the relation says which venue it holds, and it is public because a bidder must find the host of a
venue to call it. The relation is what the role is founded on: the shape the market ships beside the
role asks for `market:hosts`, so a host that hosts nothing is refused at onboarding, and the two
agree wherever both exist. A bidder in one venue may host another.

Declared, the role loads what a host needs: it is beneath the planner, the executor, the speaker and
the deliberator, since the market's actions say documents and its rules conclude what they mean
([role](/domain/kernel/role.md)).

# What it holds

Two standing desires about the documents its peers say beside the ones it says itself:

- **no call on a venue I host is left unanswered** — met by Offering a round and Clearing it;
- **no claim presented to me is left unserved** — met by Serving, which also commands its own
  valve.

Each desire's met-test is a `sh:sparql` constraint over the documents, and each call or
presentation that arrives is an instance the derivation mints a want for — the host sources none
of its wants itself.

# What it does not do

Decide who needs the good. The lot is sized by what the host chose to put up, the price by the
bids, and the round by the calls; nothing it does reads a bidder's reading.

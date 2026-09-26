---
type: Role
title: Host
term: http://example.org/orexis/market#hosts
description: >-
  The agent that holds a venue's good - it offers and clears the rounds and serves the claims. A
  role a world states with `market:hosts`, played by whoever holds the stock; its two desires, no
  call unanswered and no presented claim unserved, are all it does on the market.
---

# What it is

`:supplier market:hosts :water`. The host is whoever the world says holds the good; a bidder in
one venue may host another. It holds two standing desires about the documents its peers say beside
the ones it says itself:

- **no call on a venue I host is left unanswered** — met by Offering a round and Clearing it;
- **no claim presented to me is left unserved** — met by Serving, which also commands its own
  valve.

Each desire's met-test is a `sh:sparql` constraint over the documents, and each call or
presentation that arrives is an instance the derivation mints a want for — the host sources none
of its wants itself.

# What it does not do

Decide who needs the good. The lot is sized by what the host chose to put up, the price by the
bids, and the round by the calls; nothing it does reads a bidder's reading.

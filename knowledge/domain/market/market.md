---
type: Domain Concept
title: Market
term: http://example.org/orexis/market#Market
description: >-
  A venue - one place a scarce good is traded, hosted by the agent that holds it and bid in by
  agents that want it. A domain of files - five kinds of document agents say to one another, five
  rules concluding what the documents mean, six actions - and no Python. `domains/market/`.
---

# The standing structure

A world states it:

```turtle
:water a market:Market ; market:aboutProperty climate:SoilMoisture ;
    market:lotL 0.5 ; market:reservePerL 1.0 ; market:bidWindowS 30 .
:supplier market:hosts :water .
:fern_grower market:bidsIn :water ; market:valuePerL 3.0 .
```

`market:hosts` names the agent that holds the good, runs the rounds and serves the claims;
`market:bidsIn` an agent that may call and tender. What one round sells (`market:lotL`), the least
price a bid must offer (`market:reservePerL`) and how long a round stands open
(`market:bidWindowS`) are the host's picks. What a litre is worth to a bidder, `market:valuePerL`,
is the bidder's own belief and what it bids.

# What happens on it

The [auction](/domain/market/auction.md): a bidder calls, the host offers a round, bidders tender,
the host clears it and tells each winner its claim, a holder presents a claim when it needs the
good, and the host serves it. Every one of those is an action whose taking says a document to a
peer ([speech](/domain/speech/speech.md)), and every fact a plan speaks about the market is a revision
the rules conclude of the documents — a venue is `market:open` while a round stands on it uncleared,
an agent `market:holdsClaimOn` a venue until its claim is discharged.

Nothing is signed: the host serves only a claim its own said documents hold, and which peer spoke
is the seam the transport leaves.

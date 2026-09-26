---
type: Domain Concept
title: Call
term: http://example.org/orexis/market#Call
description: >-
  A bidder saying a round is wanted on a venue, because its subject is in trouble - a
  `market:CallGraph` said to the host. The host's desire that no call goes unanswered reads it,
  so a call is a want arriving at the host, which the host plans for like any other.
---

# What it is

```trig
:call_fern_1 { :call_fern_1_c a market:Call ; market:calledOn :water ;
               market:calledBy :fern_grower ; market:calledAt "…"^^xsd:dateTime . }
```

Said by `market:Calling`, which a bidder's search reaches for when its soil is below its range and
it holds no claim on a venue it bids in. The host believes it through `heard`, and its desire *no
call on a venue I host is left unanswered* reads it unmet — a want the derivation mints, and the
host's search answers with Offering and Clearing.

# What it comes to

The rules conclude `market:offered` while a round answering it stands open, and `market:answered`
once that round has cleared. An answered call is met; a call nobody could answer stands until
one can.

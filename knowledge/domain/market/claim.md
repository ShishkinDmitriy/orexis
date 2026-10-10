---
type: Domain Concept
title: Claim
term: http://example.org/orexis/market#Claim
description: >-
  What a winner holds after a clearing - an amount of the good at a price, owed by the host until
  it is served. The host says it to the winner and keeps its own copy, which is its debt; the
  holder presents it when its subject needs the good, and the host serves it and says it again,
  discharged.
---

# What it is

A `market:ClaimGraph`: `market:heldBy` the winner, `market:onVenue`, `market:amountL`,
`market:pricePerL`. The rules conclude that the holder `market:holdsClaimOn` the venue until the
claim is discharged, and that is the fact a grower's plan reads when it can present rather than
bid.

# Its life

1. **Issued** at a clearing, said by the host to the winner — the host's own said copy is what it
   owes, and the one the host will serve against.
2. **Presented** — `market:Presenting` says a presentation when the holder's subject's soil is
   believed dry; the claim is then `market:presented`, and the host's desire *no presented claim unserved*
   reads unmet.
3. **Served** — `market:Serving` sends the dose to the host's valve through its command and says
   the claim again with `market:discharged true` and `market:dischargedAt`.

A debt is not a stronger desire: an unserved claim is a breach where an unmet want is a gap, even
though the host's search plans for both alike.

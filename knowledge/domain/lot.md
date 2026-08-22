---
type: Domain Concept
title: Lot
description: >-
  What one auction sells — a quantity of the venue's good at a reserve, both numbers the
  host's own beliefs, so a round is sized by what the seller chose to put up and never by
  what anyone needs. Bounded by the constitution's two ceilings, checked by clearing; states
  its good; one number for every round, which is a recorded seam.
---

# What it is

The **lot** is what one [auction](/domain/auction.md) sells: a quantity of the
[venue](/domain/venue.md)'s [good](/domain/good.md), put up at a reserve. Both numbers are the
[host](/domain/host.md)'s own beliefs — `market:offerQuantityL` and `market:reservePricePerL` —
and that is the substance of calling it the host's *standing offer*: what is on the table was
decided by the seller before any trouble was announced, not computed from the trouble.

# Sized by belief, never by demand

The host is deliberately blind to quantity before a round. What an agent wants, and how badly,
is a private valuation — asking for it ahead of the auction would *be* the auction — so a band
crossing picks the MOMENT a round opens and nothing about its size. Why that blindness is the
design, what the gap between announcing trouble and pricing a bid costs, and what an iterative
auction would buy instead is
[the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md).

When the bids arrive and turn out to fit inside the lot, the round fills everyone in full at
the reserve — the dispense path, computed at the one moment the numbers exist. That behaviour
is [market](/domain/market.md)'s to state.

# It states its good

A lot is a quantity OF something, and the something is a node the source states once, at class
level. What routing every denomination join through the good keeps expressible is
[good](/domain/good.md)'s; the argument is
[the-lot-states-its-good](/decisions/the-lot-states-its-good.md).

# What bounds it

Two ceilings, both the constitution's, both read by [clearing](/domain/clearing.md), neither
the host's to move mid-round:

- `market:lotCapacity` — the physical ceiling of what the venue's resource can supply. The
  domain states its own word (`water:capacityL`) as a subproperty and the closure entails the
  market's.
- `market:allocationCeilingL` — the most one participant may take in a single trade, whatever
  it bid. Derived by the domain from the span of the subject's survival range — structural, so
  clearing never needs a bidder's current state to see an over-allocation. Absent is not zero:
  a subject stating no survival range has no ceiling, and clearing checks nothing for it.

# Lots pluralise by auction, not by round

A large quantity split into pieces is several lots, each sold by an auction of its own — never
several rounds, which are passes of bidding inside one auction. Holding those two apart is
[round](/domain/round.md)'s job; what matters here is that "the lot" is singular per auction,
and the shipped world offers it undivided.

# Seams

The lot is one number for every round — it varies with nothing: not the season, not the tank
level, not how many agents are plumbed in. `market:lotCapacity` caps it physically, but nothing
connects the ceiling to the offer. The seam and its revisit trigger live in
[the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md).

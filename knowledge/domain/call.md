---
type: Domain Concept
title: Call
term: http://example.org/orexis/market#Call
description: >-
  A round is wanted on a venue, because a participant said it is in trouble. A want the host
  did not source — as a claim makes a dose owed, a LOW makes a round called for — held one per
  venue in the host's own graph, written on the verdict, retracted when a round opens there,
  and pursued by the search like any other want: Offer, or acquire upstream then Offer when the
  vessel is dry. Maximal urgency while it stands; no clock runs it down.
---

# What it is

The **want** behind the host's move. Before it existed, a participant's `LOW` was a trigger:
hosting heard it, checked a cooldown and a dict, and announced — and when the vessel was dry,
remembered the `LOW` in a second dict and announced on the next reading. That was a plan
written as a handler. A call is the same fact stated as what it is: *a round is wanted here*,
so the search can find what stands in the way.

| | |
|---|---|
| `market:calledOn` | the [venue](/domain/venue.md) |
| `market:calledBy` | who said `LOW` — the last one, where several did; prose, never a size |
| `market:calledAt` | when |

One per venue, minted from the venue's own IRI: a second `LOW` while a call stands restates
it. It is answered by a round existing — `announce` retracts it — and it is met in a plan
exactly where the `Offering` action's effect put a round.

# Whose want it is

Sourced by another agent, like an [obligation](/domain/obligation.md), and ranked in the same
currency: `HostingModule.desires()` contributes one `Desire` per call at urgency 1.0, and its
`desire_urgency` answers 0 in any world — held or imagined — where a round stands on the venue.
A call outranks nothing by policy: a dealer whose own barrel is thirsty ranks its downstream's
trouble beside it, and whether it would *rather* sell is the
[strategic-supplier](/decisions/strategic-supplier.md) seam, not a number chosen here.

# What it is not

- **Not a demand.** A `LOW` is a verdict, never a quantity — the lot is the host's standing
  offer capped by its stock, and a call carries no size
  ([the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md)).
- **Not the only shock.** [market](/domain/market.md) names four; the demand shock is the one
  that raises a call today, and each of the others would be one more writer of the same want.

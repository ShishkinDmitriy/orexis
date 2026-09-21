---
type: Domain Concept
title: Call
term: http://example.org/orexis/market#Call
description: >-
  A round is wanted on a venue, because a participant said it is in trouble. An INSTANCE the
  host did not source - as a claim makes a debt, a LOW makes a call - held one per venue in the
  host's own record, written on the verdict, retracted when a round opens there. The want is
  the derivation's, minted under the host's standing desire *no unanswered calls* exactly as a
  debt's is minted under *no overdue debts*, and pursued like any other: Offer, or acquire
  upstream then Offer when the vessel is dry.
---

# What it is

The **premise** behind the host's move. Before it existed, a participant's `LOW` was a trigger:
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

Sourced by another agent, like an [obligation](/domain/obligation.md), and reaching the search
by the same road: the host holds a standing desire over its venues, the call is the instance
that desire is about, and `derive_wants` mints one want per call with no round on it. Met
exactly where a round stands — held, or imagined by an `Offering` step of the very plan being
weighed, since the met-test names no world.

**It was LIFTED, and it was the one want here no derivation minted.** `HostingModule.desires()`
built a `Want` per call and handed it to the choir, so a call had no provenance, no graph and
no period, and what made it look ranked beside a debt was a number a capability contributed —
`desire_urgency` answering 0 where a round stood. That number is gone
([a-want-is-judged-by-its-met-test-and-nothing-else](/decisions/a-want-is-judged-by-its-met-test-and-nothing-else.md)),
and with it the last reader of a measure. A call outranks nothing, and nothing outranks it: a
dealer whose own barrel is thirsty has both wants and plans for both, and whether it would
*rather* sell is the [strategic-supplier](/decisions/strategic-supplier.md) seam.

# What it is not

- **Not a demand.** A `LOW` is a verdict, never a quantity — the lot is the host's standing
  offer capped by its stock, and a call carries no size
  ([the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md)).
- **Not the only shock.** [market](/domain/market.md) names four; the demand shock is the one
  that raises a call today, and each of the others would be one more writer of the same want.

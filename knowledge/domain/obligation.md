---
type: Domain Concept
title: Obligation
description: >-
  A desire this agent did not source — what it OWES because the society issued a claim against
  its hardware. BOID's O, recorded in a graph of its own with the counterparty, the claim that
  caused it, whether it has been demanded, and when it was discharged; kept after payment,
  because a debt paid and a debt forgotten must not look alike. Two levels, and the split is the
  point: whom I MAY owe is topology, derived from the wiring exactly as the broker ACL is, so a
  debt to an agent the world does not declare is refused before it becomes a desire. What I owe NOW
  is runtime state, private, and disclosed the way everything private is — the sovereign asks.
---

# What it is

An **obligation** is a desire that arrived from outside. When the society issues a
[claim](/domain/claim.md) against this agent's hardware, the agent **owes** — and that owing is
recorded as a first-class thing rather than inferred from the claim whenever somebody looks.

It carries the counterparty, the claim that caused it, whether it has been demanded yet, and when
it was discharged. **Kept after payment**, because a debt paid and a debt forgotten must not look
alike.

# It is a desire, and calling it one is the design

BOID's O, and the reason the desire-graph class was a *class* from the start. An obligation is
scored, ranked and pursued by the same machinery an agent's own wants are: it has an
[urgency](/domain/urgency.md), it appears in *what am I pursuing*, and it competes for attention
on the same scale.

Since [#471](https://github.com/ShishkinDmitriy/orexis/issues/471) that is structural rather
than taxonomic: there is **no Obligation class**. An obligation is an `orexis:Desire` whose
premises are a claim and a counterparty — the kind is read off them, never off a type — and
rows written before the fold keep the retired type harmlessly, because no reader asks.

What differs is only **whose it is** and **whether there is anyone to be wronged**. An agent that
lets its own aim slip disappoints itself; an agent that lets an obligation slip defaults on
somebody.

# Two levels, and the split is the point

**Whom I may owe is topology.** It is derived from the wiring that says who may present to this
agent — exactly as the broker ACL is derived — so a debt to an agent the world does not declare is
**refused before it becomes a desire**. There is no runtime check for a bogus creditor, because a
bogus creditor cannot produce an obligation in the first place.

**What I owe now is runtime state.** Private, like the intention ledger, and disclosed the same
way: the [sovereign](/domain/sovereign.md) asks.

# Its urgency is the room between two things

A obligation does not have a gap, so its urgency comes from elsewhere: **how much room is left** between
now and when it must be discharged. That is why an obligation carries both instants rather than
one — an agent holding only the deadline could not say how urgent it is without knowing when the
clock started.

Since [#472](https://github.com/ShishkinDmitriy/orexis/issues/472) the room is also the want's
declared SCOPE — `orexis:scope orexis:Within` — and the planner holds a candidate plan's landing
time to it: a serve that would land after expiry is discarded in the search, not discovered at
the venue.

# It is actionable because it names a creditor

The counterparty is not decoration on the record — it is the key that finds the lever, through the
rows of the menu that name whom they serve. [affordance](/domain/affordance.md) has that mechanism.

What it buys is that an agent does not search for a way to pay a debt. It reads one.

# Related

- [claim](/domain/claim.md) — what creates one.
- [host](/domain/host.md) — the role that accumulates them.
- [urgency](/domain/urgency.md) — the currency it competes in.
- [an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md).

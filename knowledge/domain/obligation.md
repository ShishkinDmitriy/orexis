---
type: Domain Concept
title: Obligation
description: >-
  A debt this agent did not choose — what it OWES because the society issued a claim against
  its hardware, and what the host's one desire, no overdue debts, is about. BOID's O, recorded in a graph of its own with the counterparty, the claim that
  caused it, whether it has been demanded, and when it was discharged; kept after payment,
  because a debt paid and a debt forgotten must not look alike. Two levels, and the split is the
  point: whom I MAY owe is topology, derived from the wiring exactly as the broker ACL is, so a
  debt to an agent the world does not declare is refused before it is recorded. What I owe NOW
  is runtime state, private, and disclosed the way everything private is — the sovereign asks.
---

# What it is

An **obligation** is a debt that arrived from outside. When the society issues a
[claim](/domain/claim.md) against this agent's hardware, the agent **owes** — and that owing is
recorded as a first-class thing rather than inferred from the claim whenever somebody looks.

It carries the counterparty, the claim that caused it, whether it has been demanded yet, and when
it was discharged. **A graph of its own, holding from its issue to the claim's expiry** (#645), with a
PREDICTION beside it — `market:lapsesAt`, a graph holding from the deadline on — which is what
the derivation reads to mint the want under *no overdue debts*, about this debt and holding at
that instant; the debt itself is an instance and no want
([one-function-mints-every-want](/decisions/one-function-mints-every-want.md)). Past its expiry no
reader is handed it, and the one sweep drops
it — after the ledger's keeper writes into the untimed obligations record what it came to,
`market:dischargedAt` carried over for a debt paid or `market:lapsedAt` for one the holder
never presented. **The verdict is kept, not the want**, because a debt paid and a debt
forgotten must not look alike; `Ower.settled` is the sovereign's door to it.

# It is the host's predicted arrival

Since [a-claim-is-water-at-a-time](/decisions/a-claim-is-water-at-a-time.md) a debt says from
when its holder may come — `market:owedFrom`, the claim's usable instant — and that makes it
an occurrence about a window: the holder will come for these litres inside it. The claims a
host issued are its demand, and the vessel's drift reads the ledger to say when the stock
leaves its region as the windows open, so a host foresees its refill as a plant foresees a
dose. A debt discharged is not an arrival.

# It is an instance of the desire, and the want under it is pursued as any

BOID's O, and the reason the desire-graph class was a *class* from the start. An obligation is
scored, ranked and pursued by the same machinery an agent's own wants are: it has an
urgency, it appears in *what am I pursuing*, and it competes for attention
on the same scale.

Since [#471](https://github.com/ShishkinDmitriy/orexis/issues/471) that is structural rather
than taxonomic: there is **no Obligation class** — and since the derivation, no kernel type on the
row at all. The debt is what the host's desire is ABOUT, one instance of *no overdue debts*;
the derivation mints a want under that desire about this debt, and the ledger speaks for that want —
the claim, the counterparty, how far the window has run. The kind is read off the record's
premises, never off a type, and rows written before the fold keep the retired type
harmlessly, because no reader asks.

What differs is only **whose it is** and **whether there is anyone to be wronged**. An agent that
lets its own aim slip disappoints itself; an agent that lets an obligation slip defaults on
somebody.

# Two levels, and the split is the point

**Whom I may owe is topology.** It is derived from the wiring that says who may present to this
agent — exactly as the broker ACL is derived — so a debt to an agent the world does not declare is
**refused before it is recorded**. There is no runtime check for a bogus creditor, because a
bogus creditor cannot produce an obligation in the first place.

**What I owe now is runtime state.** Private, like the intention ledger, and disclosed the same
way: the [sovereign](/domain/sovereign.md) asks.

# Its urgency is the room between two things

A obligation does not have a gap, so its urgency comes from elsewhere: **how much room is left** between
now and when it must be discharged. That is why an obligation carries both instants rather than
one — an agent holding only the deadline could not say how urgent it is without knowing when the
clock started.

Since [#472](https://github.com/ShishkinDmitriy/orexis/issues/472) the room is also the want's
declared WINDOW — the period its graph holds during — and the planner holds a candidate plan's landing
time to it: a serve that would land after expiry is discarded in the search, not discovered at
the venue.

# It is actionable because it names a creditor

The counterparty is not decoration on the record — it is the key that finds the action. The
market's serve joins its row to the want that is about the debt and reads whom the debt is owed
to, so the row names the want it serves and whom for, and the search takes it by the want's
name as it takes any row that names one; [step](/domain/step.md) has that mechanism,
and nothing in the kernel knows what a counterparty is.

What it buys is that an agent does not search for a way to pay a debt. It reads one.

# Related

- [claim](/domain/claim.md) — what creates one.
- [host](/domain/host.md) — the role that accumulates them.
- urgency — the currency it competes in.
- [an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md).

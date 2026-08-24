---
type: Domain Concept
title: Urgency
description: >-
  The common currency — one scalar from 0 to 1 that makes unlike wants comparable, so the hottest
  one wins without anything having to rank kinds of want against each other. It has several
  SOURCES and one meaning: the desire's own declared measure for a measured property — distance
  from the aim, scaled by the survival room on that side — a deadline's approach for a duty, and
  1.0 flat for not knowing, which is the choice that makes an agent look before it acts. Every
  consumer reads the same number — the cadence tightens on it, the bidder prices with it, the
  planner scores worlds by it — so a change in how it is computed moves the whole society at
  once, deliberately.
---

# What it is

**Urgency is one number between 0 and 1, and it is what makes unlike wants comparable.** A
moisture [gap](/domain/gap.md), a debt with a deadline and a property nobody has looked at are
three different kinds of thing; urgency is what lets an agent say which one to deal with first
without anybody writing down a precedence between kinds.

That is the whole job: **a common currency, so the hottest want wins.**

# It has several sources and one meaning

| the desire | where its urgency comes from |
|---|---|
| a measured property | its own declared measure — distance from the [aim](/domain/aim.md), scaled by the survival room on that side, zero at the pick |
| a duty owed to a peer | the room left before its deadline |
| a property never read | **1.0** — flat |
| a commitment whose world has not answered yet | **1.0**, while the watch is open |

The sources differ; the meaning does not. A 0.8 from a deadline and a 0.8 from a dry pot are the
same claim on the agent's attention, and that equivalence is deliberate rather than a convenience.

# Not knowing is maximal, and that is the load-bearing choice

`urgency(None)` is **1.0**, not 0.0. A property nobody has read is the most urgent thing an agent
has, which is why the first intention it ever adopts is to look.

Every plausible alternative makes a system act on a value it does not have. A default is a guess; a
zero is a claim of contentment; a last-known-good outlives whatever made it good. The tempting
softness here is what makes something water a plant it has never measured.

The same reasoning gives an open watch maximum urgency: a commitment the world has not yet answered
keeps the cadence tight until it does.

# Everything steers by it, which is the point and the risk

Urgency is not a planning detail. **The cadence tightens on it** — a plant in trouble reads every
thirty seconds and a content one every ten minutes. **The bidder prices with it.** **The planner
scores possible worlds by it**, rather than by counting violations, because a dose that moves a
fern from 0.30 to 0.44 leaves the same single violation it started with and a planner counting
would refuse every dose too small to finish the job.

So a change in how urgency is computed moves the whole society at once. That is the reason it is
one definition asked of one owner rather than a formula each consumer keeps — since
[a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md), literally one
text: the desire declares its measure in the graph, and every consumer evaluates that, against
whichever world it is judging — and the reason the tests hold the compiled query and the
reference arithmetic to the same answer.

# It is contributed, not only computed

`Module.urgency()` is a [choir](/domain/choir.md) hook. Any module
may raise the urgency of a (subject, property) it can see something about, and the agent takes the
highest. So a capability that knows a reason to hurry does not need a path into the deliberator —
it answers when asked.

# Related

- [gap](/domain/gap.md) — the source of it for a measured property, and where |gap| = urgency is
  stated.
- [obligation](/domain/obligation.md) — the source of it for a duty.
- [sensing](/domain/sensing.md) — the consumer that turns it into a cadence.

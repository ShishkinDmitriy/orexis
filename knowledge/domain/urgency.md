---
type: Domain Concept
title: Urgency
description: >-
  The common currency — one scalar from 0 to 1 that makes unlike wants comparable, so the hottest
  one wins without anything having to rank kinds of want against each other. It has several
  SOURCES and one meaning: the desire's own declared measure for a measured property — distance
  from the aim, scaled by the survival room on that side — a deadline's approach for an obligation, and
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
| an obligation owed to a peer | the room left before its deadline |
| a property never read | **1.0** — flat |
| a commitment whose world has not answered yet | **1.0**, while the watch is open |
| a want met AT an instant, derived from a predicted crossing | the fraction of the stretch from its derivation to the instant that has run — never less than its root's own measure |

The sources differ; the meaning does not. A 0.8 from a deadline and a 0.8 from a dry pot are the
same claim on the agent's attention, and that equivalence is deliberate rather than a convenience.

Since the binding axis landed
([shall-must-and-may-are-not-strengths-of-one-scale](/decisions/shall-must-and-may-are-not-strengths-of-one-scale.md),
#472), the table's pattern has a name: **urgency is the fraction of the want's ROOM consumed,
and the binding names which room.** An `orexis:Always` want's room is STATE — the survival
envelope, so its urgency is the instantaneous degree of being off, a state function that moves
only when the world moves. An `orexis:Within` want's room is TIME — the redeem window, so its
urgency rises in a frozen world, which is why lapsing is judged by the reader's clock. An
`orexis:At` want's room is time too, the stretch to its instant, opened when the crossing was
foreseen ([root desire](/domain/root-desire.md)). And not
knowing consumes the whole of either, which is what maximal always meant. One meaning, two
projections — the stake and the debt formulas were never two ideas.

The corollary explains an absence: an `orexis:AtEnd` want with no deadline has no room being
consumed, so nothing makes it urgent — and a want with no urgency never wins attention. That is
the quiet reason no derivation writes one; a real AtEnd customer must declare its heat or
borrow a clock, at which point it is really a Within. The customer that arrived is the want
derived under a root when its shape is violated: it borrows the root's state room rather than
declaring heat of its own ([an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it](/decisions/an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it.md)).

# How much unmet, when the want is not a number

The met-shape says WHETHER (conformance is boolean); this number says HOW BADLY — and for a
want that is not about a number, *how badly* has exactly four honest sources, every want
falling to one:

| the want's shape | its measure |
|---|---|
| a number a lever moves incrementally | **distance** — partial progress must rank, or a dose too small to finish is refused |
| no metric, but a deadline | **the clock** — when state has no dimension, time is the room being consumed |
| no intermediate worlds at all — discharged-or-not, fresh-or-not | **binary**, and that is sufficiency rather than a stopgap: a gradient earns its place only where part-way worlds exist and a lever can reach them |
| a composite pattern — *all my debts honoured* | **decomposition** — the forest's roll-up: how much becomes how many leaves, and how hot, each leaf bottoming out in a row above |

Beneath all four sits the loud default: a want nobody measures scores maximal, logged.

Binary is enough for two structural reasons. The search never needed a gradient to cross an
unmet valley — the frontier carries partial steps regardless of score, which is how
refill-then-serve is found while the refill itself still scores 1.0 — and under the two-stage
ranking a binary want's plan choice is achievement plus cost, no *how much* consulted. The
gradient's one irreplaceable job is ranking partial ENDINGS, and only metric wants have those.

And one refusal, written before anyone proposes it: no generic graph-distance — *how many
triples short of matching* — ever. It is arithmetic nobody owns, incomparable to this common
currency, and the counting mistake in disguise. Where partial progress in a pattern must
rank, decompose the pattern into leaves; never mint a metric over it.

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
text and one owner: [sensing](/domain/sensing.md) declares and runs the measure for anything
observation-backed, every consumer asks the choir (`desire_urgency`) about whichever world it
is judging, and the kernel holds no measure of its own — which is the reason the tests hold
the declared query and the reference arithmetic to the same answer.

# It is contributed, not only computed

`urgency` is a [choir](/domain/choir.md) hook — sensing's, asked through `Agent.ask`. Any module
may raise the urgency of a (subject, property) it can see something about, and sensing takes the
highest; the keeper adds the maximum while a watch is open on any want about the property. So a capability that knows a reason to hurry does not need a path into the deliberator —
it answers when asked.

# Related

- [gap](/domain/gap.md) — the source of it for a measured property, and where |gap| = urgency is
  stated.
- [obligation](/domain/obligation.md) — the source of it for an obligation.
- [sensing](/domain/sensing.md) — the consumer that turns it into a cadence.

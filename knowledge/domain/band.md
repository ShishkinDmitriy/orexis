---
type: Domain Concept
title: Band
term: http://example.org/orexis/water#Band
description: >-
  One of the zones a region divides a property into — LOW, OK, HIGH, and past the envelope —
  and the agent's verdict about its own subject rather than a fact about the number.
  Desire-relative by construction: the same 0.30 is LOW for a fern and OK for a succulent,
  because their subjects need different things. Since #576 a band is a CLASS of readings the
  domain declares, minted per (subject, property) at genesis from the range the world states
  and asserted on a reading by entailment when it is written or imagined — never a second
  copy of the number, a conclusion the vocabulary draws and drops with the node. What retired
  is `ag:bandLow` and `ag:bandHigh`, two hand-picked decimals in an agent's beliefs, and not
  the word: a band is on the wire, in the firmware, read by a host deciding whether to convene,
  and now what a plan's precondition says a reading IS.
---

# What it is

A **band** is one of three zones a [region](/domain/region.md) divides a property into: `LOW`
below it, `OK` inside, `HIGH` above.

It is a **verdict, not a measurement**. The [reading](/domain/reading.md) is what an instrument
said; the band is what this agent makes of it. So the same 0.30 is LOW for a fern and OK for a
succulent — which is what the word always meant here, except that the difference is now stated
publicly by the subjects rather than implicitly by numbers nobody could check.

**Never a second copy of the number.** The verdict is a conclusion the vocabulary draws from the
region and the reading, and since #576 it is drawn by ENTAILMENT and asserted on the reading's
node — when the sensed writer writes one, when a possible world forks one, when a volume boots —
and gone with the node at the next upsert. It cannot disagree with the two facts it comes from,
because it is not kept apart from them.

# As classes, since #576

Deliberation is on triples and a number is not special
([deliberation-is-on-triples-and-a-number-is-not-special](/decisions/deliberation-is-on-triples-and-a-number-is-not-special.md)),
and what a reading can be is decided inside the domain. Sensing declares the FAMILIES as classes
of observations: `sensing:BelowRegion`, `sensing:InRegion`, `sensing:AboveRegion`, and past the
envelope `sensing:BelowFloor` and `sensing:AboveCeiling`, each also below or above the region. A
MEMBER is minted per (subject, property) that states a range, at genesis by sensing's `rules.ru`,
defined in OWL — an intersection of the observation class, the subject and the property by
`owl:hasValue`, and the result by a datatype restriction with the range's own bounds — so an
outside reasoner reads exactly what the store asserts. The store's entailment door
(`Store.entail`) is the second OWL construct materialised here, beside the closure's
`owl:hasValue`.

What the search does with it: a present is matched to a kept world by the bands its readings are
in ([identification](/domain/identification.md)); a step's [precondition](/domain/precondition.md)
states the standing reading by its band, one triple; a [remembered plan](/domain/remembered-plan.md)
is keyed by that; and a predicted reading carries its band beside its number in the step's
prediction. What the search does NOT yet do with it is plan on it alone: the number still moves
a possible world, until [#579](https://github.com/ShishkinDmitriy/orexis/issues/579) takes the
number out of the effect.

The cell of #573 — a partition the kernel read off the readers' constants — was this concept
without its owner, and is gone.

# Whose verdict it is

Not the sensing loop's, and not the device's. Sensing asks whoever holds a stake in the property
and passes the answer on **without reading it** — so an agent with no stake contributes nothing
and its device is told only a cadence.

That is why a band is a fact about the *pot*, not about the *probe*: it exists because something
wants something, and where nothing wants anything there is no band to compute.

# Two things on the wire, one concept

Easy to read as two, and they are the label and the boundaries of the same zones:

- **which band a reading is in** — announced to peers, and shown by a board that can display it.
  A [host](/domain/host.md) reads it to know a round should open: `LOW` announces trouble rather
  than a quantity, which is what keeps convening free of anyone's arithmetic.
- **where the bands END** — the pair a board is armed with, so it can wake the instant a value
  leaves one instead of waiting for its next scheduled look.

How both travel, why they ride the cadence message rather than a channel of their own, and what
retention buys a board that deep-sleeps are all [sensing](/domain/sensing.md)'s.

# What retired, and what did not

`ag:bandLow` and `ag:bandHigh` are **gone**. A band's edges used to be two hand-picked decimals
sitting in an agent's beliefs; they are the deduced [region](/domain/region.md)'s edges now. The
world files say so themselves — *"the bands that used to sit here are gone."*

**The word did not retire with them.** A page listing "target, band, endowment" among an agent's
stored beliefs is describing a design that ended; a page saying a board is told its bands is
describing what runs today. The first is stale, the second is correct, and telling them apart is
the whole reason this page exists.

# Related

- [region](/domain/region.md) — what divides a property into bands.
- [sensing](/domain/sensing.md) — how the verdict reaches peers and boards.
- [desire](/domain/desire.md) — who is asked for it.

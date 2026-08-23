---
type: Domain Concept
title: Band
term: http://example.org/orexis/water#Band
description: >-
  One of the three zones a region divides a property into — LOW, OK, HIGH — and the agent's
  verdict about its own subject rather than a fact about the number. Desire-relative by
  construction: the same 0.30 is LOW for a fern and OK for a succulent, because their subjects
  need different things. NEVER STORED, always recomputed from the region and the reading, so
  there is no second copy to fall out of step. What retired is `ag:bandLow` and `ag:bandHigh` —
  two hand-picked decimals in an agent's beliefs — and not the word: a band is still what it
  always was, and it is on the wire, in the firmware, and read by a host deciding whether to
  convene.
---

# What it is

A **band** is one of three zones a [region](/domain/region.md) divides a property into: `LOW`
below it, `OK` inside, `HIGH` above.

It is a **verdict, not a measurement**. The [reading](/domain/reading.md) is what an instrument
said; the band is what this agent makes of it. So the same 0.30 is LOW for a fern and OK for a
succulent — which is what the word always meant here, except that the difference is now stated
publicly by the subjects rather than implicitly by numbers nobody could check.

**Never stored, always recomputed** from the region and the current reading. There is no second
copy that could disagree with the two facts it comes from.

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

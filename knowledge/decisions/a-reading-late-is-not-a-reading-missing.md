---
type: Decision
title: A reading late is not a reading missing — an observation holds a grace past its due
description: >-
  An observation held exactly until the next was due, so a reading published a moment late left the
  agent with no present, and a dose taken then commanded nothing. It now holds one cadence past due,
  and its successor still replaces it the moment it lands.
status: accepted
timestamp: 2026-10-03T16:30:00Z
---

# What was wrong

`received` wrote each [observation](/domain/sensing/observation.md) holding from its instant until
the next was due by its sensor's `ssn-system:Frequency`, and not a moment longer. Every reading
that arrives a little late opens a hole: a board's radio, a broker, or a simulator's loop delays
the successor, and until it lands, a reader asking at the present instant is handed nothing of
that sensor. The #47 spike measured it. At a pace where the cadence was shorter than the
simulator's loop, the grower held no present moisture reading two thirds of the time, and the dose
it took sized itself from nothing (#869 made that step fail instead of passing as taken). At pace
one the hole is seconds wide in ten minutes, but it is the same hole, and nothing was closing it.

# What it is now

The period ends at the next due instant **and a grace past it**: one cadence (`received.GRACE`).
Its successor still replaces it whole the moment it arrives, so at most one observation of a key
ever holds. That is the property
[a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md) named as the one
to keep "if readings ever move": validity until the next observation, non-overlapping by
construction. A late reading is the promise kept a little late; past the grace the reading is
missing, which is what `missed` answers; and `sensing:silentAfter` cadences past that (`SILENT_AFTER` where the world states none), the sensor is
silent.

Two things move with the period's end, because the end was their hinge as well. `missed` says a
reading is missing a cadence later than it did. Prediction's first stretch opens where the
observation's period ends, so the stretch from due to due-plus-grace reads the last observed number
instead of the first predicted one. That is the present as the agent last saw it. No test of
planning or prediction moved with it; the one world test that did is the terrace's, whose board is
said silent a cadence later.

# What was refused

- **Open-ended until the successor arrives.** The period would end only when replaced or silenced,
  with no clock end. But the end is also when prediction's first stretch opens, and prediction
  imports nothing of sensing. Holding open would leave prediction asking sensing's words for when
  the next reading is due, or would stack the first prediction on top of an observation that still
  holds. That is a larger change across two packages, for a difference a bounded grace already
  covers.
- **Leaving the period exact and failing loudly in the hole.** #869 already stops a step taken in
  the hole from passing as taken. But a reading a moment late is not an absent reading, and every
  reader of the present met the hole, not only a command: a met-test, the executor's answer to a
  step, a ground laid at that instant.

# Seams left open

- **The grace is one cadence for every sensor.** A sensor that is reliably late by more, such as a
  board that sleeps past its interval to save a battery, would want its own, stated by its world in
  SSN-System's words. Nothing reads such a statement yet.

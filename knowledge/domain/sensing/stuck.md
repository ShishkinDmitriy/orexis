---
type: Domain Concept
title: Stuck
term: http://example.org/orexis/sensing#stuckSince
description: >-
  A sensor that keeps reporting and reports the same number every time - a frozen oscillator, a
  half-lost wire - is stuck. Said by sensing of a sensor whose number has not changed for a limit of
  its cadences, in a graph of the agent's own that a differing reading drops. The second doubt the
  belief base holds about a reading, beside its age.
---

# What it is

```turtle
# the keeper's graph for the probe, an orexis:StateGraph holding from the run's start
:probe sensing:stuckSince "2026-01-01T12:00:00Z"^^xsd:dateTime .
```

A sensor's number is `sensing:rawResult` on its [observation](/domain/sensing/observation.md),
the count or degrees the pointer found in its bytes before any
[scaling](/domain/sensing/scaling.md). Two readings are **indistinguishable** when that number is
identical - not the [reading](/domain/sensing/reading.md) concluded from it, which a clamp or a
rescale could make identical out of two different counts, and not close, since a live instrument
jitters by at least a count and that jitter is what a stuck one lacks. `received` writes on each
observation `sensing:unchangedSince`, the instant of the earliest reading in the unbroken run of
this number - its own instant where the number differs from the one before - so the run's start
survives the replacement of the observation and a restart alike, and nothing is counted in Python.

A sensor whose run has lasted `sensing:stuckAfter` of its cadences — the limit the agent's world
states of it, six where it states none — is said stuck: one row,
`sensing:stuckSince` the run's start, in a graph of the agent's own classified `orexis:StateGraph`,
holding from that instant - named for the state and never for the reading that tipped it - and
said once. A reading whose number differs ends the run and takes the graph with it, at the writer.
A sensor stating no `ssn-system:Frequency` is never said stuck, as it is never said silent: the
limit is in cadences, and the world made no promise about how often its number would have the
chance to move.

# Why it is its own doubt

Freshness is the age of an observation, and the silence `missed` says is the one doubt the store
held about a sensor until #462: a probe that keeps REPORTING was trusted for as long as it
reported. The terrace's probe lost half its wire at mounting and gave a plausible number, on time,
all night, and every gate stayed green. Stuck is the other failure of an instrument, the signal
being wrong while it is fresh, and it is said beside the silence and not inside it: a silent
sensor has no present, a stuck one has a present not to be believed, and a plan that branches on
either branches on a different row.

# What it leaves to others

Nothing here says what to DO about a stuck sensor. The row is a belief a desire's met-test may
read and a plan may branch on, and what a world makes of one is the world's. Two readings a count
apart are two readings, so a connection that creeps rather than freezes is not caught here: that
is what publishing the raw number unclamped (#462's first detector) and the board's other sensors
moving while this one does not (its third) are for.

The premise is the instrument's to keep, and a simulated one keeps it too. The simulator
(`simulation/simulator.py`) publishes each number with the instrument's noise — a seeded draw
within the model's `sim:jitter` either way, never the number that sensor published last — because
the model's reading moves only where the physics moves it, and a thermometer in a greenhouse
nobody heats was said stuck an hour into its world (#879). The limit is the agent's, stated of it
by its world; a simulated world that read as stuck was a quiet instrument, not a low limit, and
`sensing:stuckAfter` is not where that is fixed.

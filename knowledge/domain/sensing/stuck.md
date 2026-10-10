---
type: Domain Concept
title: Stuck
term: http://example.org/orexis/sensing#stuckOn
description: >-
  A sensor that keeps reporting and reports the same number every time - a frozen oscillator, a
  half-lost wire - is stuck. Said by sensing's rule of a sensor whose last sensing:stuckAfter readings,
  every percept of it kept, all gave one raw number, in the revision of the latest, so it holds while
  that percept does. It counts readings, not time. The second doubt the agent holds about a reading,
  beside its age.
---

# What it is

```turtle
# the revision of the probe's latest percept, as sensing's rule concludes it
:probe sensing:stuckOn 2412 .
```

A sensor's number is `sensing:rawResult` on its [observation](/domain/sensing/observation.md),
the count or degrees the pointer found in its bytes before any
[scaling](/domain/sensing/scaling.md). Two readings are **indistinguishable** when that number is
identical - not the [reading](/domain/sensing/reading.md) concluded from it, which a clamp or a
rescale could make identical out of two different counts, and not close, since a live instrument
jitters by at least a count and that jitter is what a stuck one lacks.

Sensing keeps a sensor's last `sensing:stuckAfter` [percepts](/domain/sensing/observation.md) — a
[stance](/domain/kernel/stance.md), six where the agent's self graph states none — and **a rule says
the sensor stuck when every one of them gave one number**: `:probe sensing:stuckOn 2412`, the number
it is stuck on, concluded in the revision of the percept arriving (`agent/sensing/rules.ttl`). It
holds while that percept does, so the first reading whose number differs ends it — the kept percepts
no longer agree — and so does a silence, since a silent sensor has no percept holding. Nothing counts
a run and nothing carries one onto the present: the premise is the percepts themselves, and the rule
reads them where sensing keeps them, with the limit off the self graph, the one rule of sensing's
that reaches past the arrival it is revised for. A sensor stating no `ssn-system:Frequency` is never
said stuck, as it is never said silent: its readings are no samples on a cadence the world promised.

**It counts readings, not time** (#944). Six readings of one number on time are stuck at the sixth,
fifty minutes after the first at the greenhouse's ten; a sensor that misses readings is said stuck
later than one that never misses, and two readings a day apart are two readings. As it was counted
before the percepts were kept, from the start of an unbroken run carried onto each observation, the
run had to last the limit in cadences, which on time was a reading later, and with readings missed,
sooner.

# Why it is its own doubt

Freshness is the age of an observation, and the silence `missed` says is the one doubt the store
held about a sensor until #462: a probe that keeps REPORTING was trusted for as long as it
reported. The terrace's probe lost half its wire at mounting and gave a plausible number, on time,
all night, and every gate stayed green. Stuck is the other failure of an instrument, the signal
being wrong while it is fresh, and it is said beside the silence and not inside it: a silent
sensor has no present, a stuck one has a present not to be believed.

# What it leaves to others

Nothing here says what to DO about a stuck sensor. It is said of a percept, so no reader of the mind
is handed it: sensing's part says it as `doubted`, which the metrics carry and reflection reads, and a world
whose plans should branch on it would need it believed — a transition making a state of it — which
none does yet. Two readings a count apart are two readings, so a connection that creeps rather than
freezes is not caught here: that is what publishing the raw number unclamped (#462's first detector)
and the board's other sensors moving while this one does not (its third) are for.

The premise is the instrument's to keep, and a simulated one keeps it too. The simulator
(`simulation/simulator.py`) publishes each number with the instrument's noise — a seeded draw
within the model's `sim:jitter` either way, never the number that sensor published last — because
the model's reading moves only where the physics moves it, and a thermometer in a greenhouse
nobody heats was said stuck an hour into its world (#879). The limit is the agent's word about
itself; a simulated world that read as stuck was a quiet instrument, not a low limit, and
`sensing:stuckAfter` is not where that is fixed.

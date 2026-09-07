---
type: Domain Concept
title: Tolerance
term: http://example.org/orexis/actuation#tolerance
description: >-
  How wide the interval an effect predicts is — a fraction of the predicted movement either
  side of the number, read by the effect rule from the agent's beliefs. Not physics but a
  belief about how good the package's conversion is, held like every belief: a pick inside
  constitutional bounds, revisable on evidence, defaulted by the capability where an agent
  states none.
---

# What it is

`actuation:tolerance`, and its twin `market:tolerance` for a bought lot and a served level.
What a step is held to is its own prediction (`progression:predicts`, [step](/domain/step.md)),
and since #556 that prediction is an [interval](/domain/interval.md) whose width is this term:
the effect rule reads it from the agent's beliefs and binds the two ends beside the number.
That is not a fact about water or soil; it is a fact about how good the model is — the
conversion a package predicts through — and so it is a [pick](/domain/pick.md): an agent's own
value inside `minTolerance`/`maxTolerance`, which the package's ontology declares and its shape
holds the pick to, exactly as `progression:patienceS` is held. An agent that states none gets
the capability's default (0.5 of the movement), the way `progression:Intention` carries
`suspectAfter`.

A FRACTION of the predicted movement rather than an absolute in the property's unit, so it is
scale-free across properties. The ends are predicted ∓ tolerance × movement: an overshoot is as
much a surprise as a shortfall, because both say the conversion is wrong, and the review is
where that evidence goes. Who reads it moved (#556): the actor used to pass its pick to the
keeper at execution, which drew the band around a point; now the rule reads the pick where the
arithmetic is, the search sees the width, and the actor passes nothing.

# Why the bounds are where they are

Below the floor, sensor noise reads as a lie — the +0.001 that once closed a watch would now
fail one. At 1.0 the band reaches back to the baseline and no movement at all would pass, so
the ceiling is the last value at which the tolerance still asks for anything.

# What it is not

**Not the met-fraction.** The kernel's met-fraction was a constant, one-sided — at least a
quarter of the actor's own delta — and it accepted any overshoot; it retired with the actor's
delta arithmetic.

**Not the instrument's grain.** A tolerance finer than the sensor can read is a promise the
world cannot keep; sensing's grain as the floor is a named seam (#518), since no sensing term
states a grain yet.

**Not moved here.** Review's rule over residuals — observed against predicted, per answered
step — re-picks the conversion when they lean one way and the tolerance when they scatter; that
is [review](/domain/review.md)'s, and each package's `review.rq` says it in its own words.

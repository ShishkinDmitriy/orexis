---
type: Domain Concept
title: Tolerance
term: http://example.org/orexis/actuation#tolerance
description: >-
  How close an observed value must land to the one a step predicted to count as the effect the
  search planned on — a fraction of the predicted movement. Not physics but a belief about how
  good the package's conversion is, held like every belief: a pick inside constitutional
  bounds, revisable on evidence, defaulted by the capability where an agent states none.
---

# What it is

`actuation:tolerance`, and its twin `market:tolerance` for a bought lot. **Not on the core's road
since #579**: a step predicts the [band](/domain/band.md) its reading will be in, and the world
either shows a reading that is one or does not, so nothing is widened at verification and the
keeper takes no tolerance from any actor. What the term still governs is a package's own
arithmetic where it sizes an act and reads its residuals. The paragraphs below describe that.

Once the expectation after a step is generated from the step's own prediction
(`progression:predicts`, [step](/domain/step.md)), the only thing left for an actor to say is how
close a number must land to be "the same effect". That is not a fact about water or soil; it is a fact about how
good the model is — the conversion a package predicts through — and so it is a
[pick](/domain/pick.md): an agent's own value inside `minTolerance`/`maxTolerance`, which the
package's ontology declares and its shape holds the pick to, exactly as `progression:patienceS` is
held. An agent that states none gets the capability's default (0.5 of the movement), the way
`progression:Intention` carries `suspectAfter`.

A FRACTION of the predicted movement rather than an absolute in the property's unit, so it is
scale-free across properties. The band is predicted ± tolerance × |predicted − baseline|: an
overshoot is as much a surprise as a shortfall, because both say the conversion is wrong, and
the review is where that evidence goes.

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

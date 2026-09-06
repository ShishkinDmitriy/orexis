---
type: Decision
title: A predicted number is an interval, and a plan that cannot be certainly met has a look in it
status: accepted
timestamp: 2026-09-06T12:00:00Z
description: >-
  The numeric half of the-future-is-a-cone. A reading is a point with a width — widened by
  staleness and by the actuator's learned tolerance — an effect declares two bounds, met means
  the interval lies inside the region, the law refuses a step whose interval can cross its
  bound, the estimate reads the worst end and the cost the cheap end, and a dose is an interval
  of litres the actor picks inside at execution. Refused — a point prediction with a tolerance
  applied at verification, which is what the code does today; a kernel-wide width; and a
  tolerance owner separate from the effect and from freshness. The plan it finds that a point
  search cannot is dose, look, dose.
---

# The claim

What the search plans on is a template, not a number. For facts that was always so — hanoi and
the courier plan over facts and their plans are already templates. For numbers it is not: the
dosing rule predicts one value, the search sizes one dose, the met test compares one number to
the region, and the actor's tolerance is applied once, at verification, as a band around the
point. Under this record a number in a possible world is an [interval](/domain/interval.md).

The example, with the simulation world's own figures — two litres per fraction of moisture, a
pot drying 0.12 a day, the last reading 0.23 six hours ago, a learned tolerance of ten percent,
and a region of 0.40 to 0.60:

| | as points | as intervals |
|---|---|---|
| present | 0.23 | 0.20 to 0.23, widened by staleness |
| one litre adds | 0.50 | 0.45 to 0.55 |
| precondition | moisture is 0.23 | moisture below 0.40 |
| a dose that lands inside | 0.54 L, one answer | 0.44 to 0.67 L, any of them |
| after it | 0.50 | 0.40 to 0.60, certainly inside |

The template reads: where moisture is below the region and I hold a pump on my subject drawing
from my source, dose within that interval of litres, and moisture is then inside the region. It
applies at any reading below the region, so it is a method with no numbers to lift.

# The plan a point search cannot find

Widen the uncertainty — a probe with twenty percent tolerance and a day-old reading — and no
single dose lands the whole interval inside the region. The interval search then finds dose,
look, dose: the look narrows the interval, and it is an action the repo already has. The point
search believes one dose suffices, the keeper reports a surprise, and a second pass finds the
second dose. Same outcome, one search later, and the plan never said a look was part of it.

The law gains the same way. Where moisture must never exceed 0.80, a point prediction of 0.78
passes and an interval of 0.70 to 0.86 is refused, which is what never-newly-enter should mean.

# What was refused

- **A point prediction with a tolerance applied at verification.** This is today: the effect
  rule binds one number, the keeper's answering shape widens it by the actuator's pick, and the
  search never sees a width. It cannot find the look, and it cannot refuse a step whose
  uncertainty crosses the law. The pick itself is kept — it is the learned width the effect
  reads — so the review loop that re-picks it on residuals is untouched; what moves is who
  reads it and when.
- **A kernel-wide width.** How wide a prediction is belongs to the effect that made it and to the
  reading it started from. A constant would be right for no actuator, which is the argument
  [the-effect-is-one-declaration-and-the-tolerance-is-a-pick](/decisions/the-effect-is-one-declaration-and-the-tolerance-is-a-pick.md)
  already made against a kernel tolerance; this record keeps that refusal and moves the pick's
  reader from the actor to the rule.
- **A tolerance owner separate from the effect and from freshness.** Identification asks whether
  the reading is inside the interval the child predicted. The interval's width is the tolerance,
  and nobody else needs one.

# What stays a specific number

The observation, which is a point with a width around it. The actor's pick at execution, one
value inside the interval, which is the one thing an actor adds. The estimate, taken at the
interval's far end, and the cost at its cheap end, so the heuristic never overstates.

# What it costs

An effect declares two bounds instead of one. Met becomes *certainly met* — the interval inside
the region — rather than possibly met. The width grows along a chain, so a long chain without a
look stops being certainly met, which is the correct behaviour rather than a defect. The
compiled select and the judge must agree on the worst end, and the engine's arithmetic on the
new literals must be measured before a column is built on it, because an operation the engine
lacks binds nothing.

# Seams left open

- **Representation** — two carried predicates on the predicted observation, so the sensing
  package declares both and the signature canonicalises a pair. A midpoint plus width was
  weighed and is the same information; the pair is chosen because every existing reader of a
  reading reads a predicate.
- **The rate that widens a reading with age** — the horizon is declared and the rate is not.
  Whose declaration it is, per sensor family, is
  [#558](https://github.com/ShishkinDmitriy/orexis/issues/558).
- **Cycle detection** — a narrower interval at the same midpoint is a new world, because a look
  is what narrows it; a look followed by a look is then two worlds, and whether that is a cost
  worth bounding is measured, not decided.
- **The residual review reads** — the midpoint, so the review rules stay as they are.

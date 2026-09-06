---
type: Domain Concept
title: Interval
description: >-
  A number in a possible world with two ends — a reading widened by its age and by the
  actuator's learned tolerance, an effect declaring what it adds as a low and a high. Met means
  the whole interval lies inside the region; the estimate reads the far end and the cost the
  cheap one; a dose is an interval of litres the actor picks inside. Not built (#556, #557, #558).
---

# What it is

The search plans on templates. For facts it always did; for numbers it plans on points today,
and the record [a-predicted-number-is-an-interval](/decisions/a-predicted-number-is-an-interval.md)
says why that is wrong and what replaces it. A number in a possible world is a pair of ends.

- **A reading** is a point with a width. The width grows with the reading's age and starts at
  the sensor's grain; a reading past its horizon is unbounded.
- **An effect** declares two bounds: what a litre adds, low and high, widened by the actuator's
  learned tolerance, which the rule reads from the agent's own beliefs.
- **Met** is the interval inside the [region](/domain/region.md), certainly. Possibly met is
  not met, and a chain that has grown too wide to be certainly met is a chain with a look in it.
- **The law** refuses a step whose interval can cross the forbidden bound.
- **The estimate** reads the far end and **the cost** the cheap end, so neither overstates.
- **A dose** is an interval of litres; the actor picks one value inside it at execution, which is
  the one thing an actor adds. This is not the alarm [band](/domain/band.md) a board keeps.

# Not built yet

The dosing rule binds one number, the keeper widens it at verification by the actor's pick, and
the search never sees a width. The issues are
[#556](https://github.com/ShishkinDmitriy/orexis/issues/556) for the effect,
[#557](https://github.com/ShishkinDmitriy/orexis/issues/557) for met, law, estimate, cost and
the dose, and [#558](https://github.com/ShishkinDmitriy/orexis/issues/558) for staleness.

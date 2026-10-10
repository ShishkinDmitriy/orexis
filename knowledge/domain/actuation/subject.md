---
type: Domain Concept
title: Subject
term: http://example.org/orexis/actuation#subject
description: >-
  What a step acts on - the bed a dose waters, the bed or frame a heating warms - and the parameter
  the dose, the heating and the market's presenting take for it. Never a reading - the subject's
  name holds still from one reading to the next, its state in a domain's words is what a precondition
  asks and an effect replaces, and its latest observation is read only by a command, when the step
  is taken.
---

# What it is

```turtle
actuation:Dosing orexis:takes actuation:valve , actuation:subject .
```

The **subject** is the thing an agent acts for (`orexis:actsFor`) and a device acts on
(`actuation:actuates`, `climate:warms`): SOSA's feature of interest, the bed. A step of the dose is
filled with the valve it opens and the subject it waters, `$subject` in the action's texts, and is
written with `actuation:subject :bed` beside `actuation:valve :pump` on the step, the
[committed step](/domain/execution/committed-step.md) and its history point. The dose, the heating
and the market's presenting each take one; the parameter is actuation's, as the
[actions](/domain/actuation/actuation.md) that act on a subject are.

# Why the subject and not a reading

The dose took the observation it answered, a parameter called the reading, until #944: its precondition asked
the reading's side, its effect deleted `below` on that observation and inserted `inside`, and its
command read the number off the same node. That made the mind speak sensing's words and depend on
how a bed's sensor is wired, and gave an action a reading for a parameter where the bed is what it
acts on ([an-observation-is-a-percept-and-the-mind-reads-only-beliefs](/decisions/an-observation-is-a-percept-and-the-mind-reads-only-beliefs.md)).
Taking the subject, each text reads what it is for:

- the **precondition** asks the subject's state in the domain's words — its
  [soil](/domain/actuation/soil.md) believed dry, its [air](/domain/actuation/air.md) cold;
- the **effect** replaces that state — dry by moist, cold by comfortable;
- **when it lands** finds the sensor the world says is hosted by the subject and observes the
  property, and its cadence;
- the **command** reads the subject's latest observation of the property, its number, when the step
  is taken — execution at the boundary, the one place on this side a number is read.

A subject's IRI is a name that does not change with every reading, so a possible world, a ground and
the present it is compared with all speak of the same node, and the scope a step falls in is keyed
by it: two beds, each with a pump, are two scopes, `(climate:soil, bed)` and `(climate:soil, bed2)`
([scope](/domain/planning/scope.md)).

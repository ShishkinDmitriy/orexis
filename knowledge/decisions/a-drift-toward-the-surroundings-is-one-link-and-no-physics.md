---
type: Decision
title: A drift toward the surroundings is one link and no physics
status: accepted
timestamp: 2026-09-12T18:00:00Z
description: >-
  The sovereign's ruling on #617, built. A sample exchanges heat with what surrounds it, and
  the world says only THAT — `climate:surroundedBy` — and how fast, `climate:degreesPerHour`.
  The direction is the sign of the gap between two readings, the speed the rate the domain
  states, and the sample stops at the surroundings' reading. The climate package's drifts do
  the rest, in the water package's two forms, and the value form says WHEN the sample leaves
  its region, which is what lets a cold night be foreseen. Refused — a coupling constant, a
  speed proportional to the gap, equilibrium arithmetic, first-order decay and its logarithm,
  and the world as a simulator; and a direction with no speed is a seam, not a drift. Two
  defects the build found in the drift's own bookkeeping are fixed beside it.
---

# The claim

**A sample exchanges heat with what surrounds it, and one link says so.** `:bed
climate:surroundedBy :outside`, and `climate:degreesPerHour 1.0` beside it, is everything the
greenhouse states about heat. From that the climate package's drift moves the bed's air toward
the outside's reading at the stated rate while nobody heats or vents, and stops when it gets
there — the direction is the sign of the gap, read from two readings; the surroundings are read
as the vent reads them, from whatever holds at the instant the world is asked about, a forecast
among them ([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)).
No coupling constant, no gap arithmetic, no curve: a heater in another room stops mattering
because the link is not there, which is a triple rather than a simulation.

**Two forms, because a reading is known two ways** — the water package's pattern
([effect](/domain/effect.md)). A reading the agent observed carries a value and moves by the
rate; one an effect predicted carries a band and no value, and crosses to the band on the
surroundings' side after the region's own width over the rate, optimistic in the direction the
world corrects, and only from inside the region, since the bands beyond it have no width to
cross.

**The value form also says when.** `orexis:crossesAfter` beside it answers, for a reading
inside its region with the surroundings beyond one edge, the seconds until it reaches that
edge — the same arithmetic asked as *when* rather than *whether*. That is what
[#619](https://github.com/ShishkinDmitriy/orexis/issues/619) reads to foresee a cold night: a
bed at twenty degrees inside its region, toward an outside at eight, one degree an hour, leaves
in two hours; a grower foreseeing six derives a want bound at that instant, and the search,
judged there, plans the heater and refuses the vent onto the cold. Toward an outside at
twenty-one the bed never leaves its region and nothing is foreseen. And a cold evening the
forecast says turns warm before the crossing warms the bed by itself at the instant, and nothing
is planned — the surroundings are read at the END of the stretch, which is the first-order
reading and the one this record keeps.

# What was refused

- **A coupling constant and a speed proportional to the gap.** First-order decay is the honest
  physics, and its crossing time is a logarithm this engine does not have; the linear form over
  a step is right where a plan is minutes against a time constant of hours, and the rate is one
  number the world can state and review can move. The coupling version is a directory that
  does not exist yet, not a rewrite of this one — a package deciding how deep it goes is rule 2
  read one level over (the issue's third comment).
- **The world as a simulator.** Coupled bodies make a possible world a vector evolving
  continuously, and identity by facts stops colliding: the day a node's instant entered the
  key, hanoi went from fifty forks to its whole budget. The plan stays qualitative, the physics
  stays a number, and they meet at the band's edge.
- **A direction with no speed as a drift.** A property with the link and no rate would say
  which way and not when, and a search plans in minutes; it is a seam, and what it might change
  is a measure, never a step's world.
- **The vent as a raising of the coupling.** It would be control-the-derivative applied to the
  one action that most visibly breaks it, and it would leave a lever whose effect the search
  cannot see. The vent keeps declaring the band it reaches (#579), and it and the drift read
  the same outside.

# What the build found, and fixed beside it

Two defects in the drift's own bookkeeping, older than the link. **A retraction was not
canonicalised like an addition**: the drift's retracted node was trimmed of the triples its
replacement re-stated, type and key among them, so what remained was two plain triples that
cancelled nothing, and a node's diff claimed the old value beside the new — a pot at 0.12 and at
0.100018 at once, unnoticed because novelty needed only a difference. The whole retracted node is
kept now. **And a step's own drift never reached its own world**: the fork was written before
the drift was computed and the diff's lists alone knew the result, so the next rule read the
world before the hour passed, and a world re-made from its lists disagreed with the first
materialisation. A step's drift is applied to its fork. A third gap was the search's, not the
drift's: the imaginarium copied the graphs holding NOW and not the table of periods, so a
forecast for a period the present has not reached was invisible inside a pass — proven at the
belief base's door and never at the search's. It copies every public graph and the table, and
filters by the instant each rule is asked at.

# Seams left open

- **The surroundings between two instants.** A drift over a stretch reads the outside once, at
  the stretch's end; a forecast that changes inside the stretch is read as its end says.
  Integration over periods is the coupling version's problem, and waits with it.
- **Two packages claiming one property.** A world installing the simple drift and a precise
  one would put two readings on one node, and nothing at genesis would notice; the gate the
  issue asks for is not built, since no second package exists.
- **Humidity.** The link is one relation and the rate is temperature's; a second rate is a
  second term when a world states one.

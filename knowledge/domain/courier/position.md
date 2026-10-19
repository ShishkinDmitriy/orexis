---
type: Domain Concept
title: Position
term: http://example.org/orexis/courier#Column
description: >-
  Where a van stands as its instruments observe it - a position fix is two sensors hosted by the van,
  one observing the column and one the row, each reporting a number; the courier's transitions
  conclude the van's `courier:x` and `courier:y` of them and then the cell authored at those
  coordinates. A position is a vector in the courier's own coordinates, a radar's relative vector is
  added to it, and a cell an instrument reports is never posed.
---

# What it is

`courier:Column` and `courier:Row` are observable properties: two `sosa:Sensor`s hosted by a van, one
observing each, are the van's **position fix**, reporting the van's `courier:x` and `courier:y` as
numbers, the coordinates every cell is authored in. An instrument gives numbers, so a position is the
two numbers a cell already has, and no second name for a cell is needed: a cell's number was built
and refused the same day (#1002), since a vector is what a fix gives and what a radar's relative
vector adds to (#1003). Where the world answers a drive, the van is told the coordinates of the cell
to reach ([driver](/domain/courier/driver.md), the two action documents).

# What the rules make of it

The courier's three [transitions](/domain/belief/transition.md) in `rules.ttl` read a fix in two orders,
because a transition is handed its one arrival and the agent's own derived state, and the two
coordinates are two arrivals. In order 0, `columnRule` and `rowRule` replace the coordinate the van is
held at with the one arriving. In order 1, `cellRule` replaces the cell the van is at with the cell
authored at the two coordinates now held - the belief every drive's effect predicts, so a commanded
drive lands when the fix has shown it. The first fix leaves the van nowhere until its second coordinate
lands, a reading later; coordinates no cell is authored at leave the cell before standing, as a state
does, until a fix says where else. The feature of interest is the van the sensor is hosted by, or what a
contact `isSampleOf` where the sensor is a radar's (#1003), whose relative vector is added to the
agent's own van's coordinates in the same shape.

**A cell a fix reports is never posed.** A transition changes the agent's DERIVED state alone, so a cell
asserted in a world's `state.ttl` would stand beside the one the fix concludes, the van on two cells and
its drive never answered (#1002, measured: every drive timed out). What comes from outside is stored when
it arrives: the lane poses its parcel's cell and its driver's van, and the van's cell is its first fix's
to say.

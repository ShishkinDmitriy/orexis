---
type: Domain Concept
title: Position
term: http://example.org/orexis/courier#Column
description: >-
  Where a thing stands - two coordinates, `courier:x` and `courier:y`, on the thing itself. A van's
  position fix is two sensors hosted by the van, one observing the column and one the row, each
  reporting a number, and the courier's transitions conclude the van's coordinates of them; a parcel,
  an obstacle, a peg and a place a parcel is owed at carry the same two. The grid is infinite and
  nothing authors it; a cell is not a thing, and a position an instrument reports is never posed.
---

# What it is

A position is two numbers on the thing that stands there: `courier:x`, its column, and `courier:y`, its
row. `courier:Column` and `courier:Row` are observable properties: two `sosa:Sensor`s hosted by a van,
one observing each, are the van's **position fix**, reporting the two numbers, and the courier's
transitions write them on the van. A parcel standing somewhere, an obstacle a radar sees, hanoi's pegs
on the tower's grid and the place a parcel is owed at (`courier:destination`) carry the same two
numbers, authored or concluded; a carried parcel carries none.

**The grid is infinite, and a cell is not a thing** (the-grid-is-infinite-and-a-position-is-two-coordinates).
Two things are neighbours where |dx| + |dy| = 1, which the drive's precondition works out by
arithmetic, minting the four neighbours of where the van stands; a parcel is where it is owed when its
two numbers are its destination's two. A node per cell was a second name for a pair the fix already
reports, and the authored set of them a map every agent was handed; the sovereign refused both, after
refusing a cell's number (#1002) and a derived adjacency (#1012). The road a world is posed on is what
STANDS on the grid, hedges a radar sees ([obstacle](/domain/courier/obstacle.md)), and an agent knows
only what it has seen.

# What the rules make of it

The courier's [transitions](/domain/belief/transition.md) in `rules.ttl` read a fix one coordinate at a
time, because a transition is handed its one arrival and the agent's own derived state, and the two
coordinates are two arrivals: `columnRule` and `rowRule` replace the coordinate the van is held at with
the one arriving, and that is the position - the belief every drive's effect predicts, so a commanded
drive lands when the fix has shown both numbers. The first fix leaves the van with one coordinate until
its second lands, a reading later, and a thing with one coordinate stands nowhere a constraint or a
met-test can read. A [contact](/domain/courier/contact.md)'s offset is added to the carrying van's
coordinates by the contact's own rules, inside the range its sensors declare.

**A position a fix reports is never posed.** A transition changes the agent's DERIVED state alone, so a
position asserted in a world's `state.ttl` would stand beside the one the fix concludes, the van at two
positions and its drive never answered (#1002, measured: every drive timed out). What comes from outside
is stored when it arrives: the lane poses its parcel's coordinates and its driver's van, and the van's
are its first fix's to say.

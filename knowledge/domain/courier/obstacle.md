---
type: Domain Concept
title: Obstacle
term: http://example.org/orexis/courier#Obstacle
description: >-
  A thing a radar sees and nothing identifies - a contact slot standing for nothing named, typed an
  obstacle by the world, at the coordinates its vector lands on while something is in range and nowhere
  otherwise. A van never stands where one is, which a world holds as a constraint, and there is nothing
  to ask it; the hedges a road is are seen this way, never known in advance.
---

# What it is

`courier:Obstacle` is the class a world gives a radar slot: a [contact](/domain/courier/contact.md)
that `isSampleOf` nothing, so what it sees has no [driver](/domain/courier/driver.md) to ask and no
plan to hear. The slot is believed at a position exactly while the simulator fills it with something in
range, a fallen tree, a van no receiver knows or a hedge beside the lane, and nowhere otherwise; nothing
types anything at runtime, since the slot is the obstacle and its position is the one belief that
changes.

# What a plan does with it

A world states, beside "no two vans stand at one position", that no van stands where an obstacle is, a
`planning:Constraint` and not a desire (`domains/courier/constraints.ttl`, held by each world's agents).
The search marks every possible world that puts the van at the obstacle's position impossible, so a
plan goes round it, and a slot filled while a plan is walking is a belief that makes the plan's next
world impossible, which reopens it (#921). In the layby's tests a tree on the direct way to the parcel
sends the van round, two drives longer, and the tree is believed nowhere again once beyond the radar's
range.

**The road is obstacles the agent discovers** (the-grid-is-infinite-and-a-position-is-two-coordinates):
the hedges either side of the lane are things the simulator poses in `domains/road/`, and no agent is
told them. A courier plans across the plane as if it were open, its radar sees a hedge within range, and
its plan is reopened where that makes the next step's world impossible. A radar sees the nearest thing
it does not identify, one per slot, so a van among several hedges believes one at a time and the
believed obstacle moves as the slot retargets; a world that needs more seen at once carries more slots.

An obstacle that moves is a seam the boat record leaves open: its position is believed where it was
last seen while it stays in range, and nothing predicts where it goes.

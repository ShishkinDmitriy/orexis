---
type: Domain Concept
title: Obstacle
term: http://example.org/orexis/courier#Obstacle
description: >-
  A thing a radar sees and nothing identifies - a contact slot standing for nothing named, typed an
  obstacle by the world, at the cell its vector lands on while something is in range and nowhere
  otherwise. A van never stands where one is, which a world holds as a constraint, and there is nothing
  to ask it.
---

# What it is

`courier:Obstacle` is the class a world gives a radar slot: a [contact](/domain/courier/contact.md)
that `isSampleOf` nothing, so what it sees has no [driver](/domain/courier/driver.md) to ask and no
plan to hear. The slot is believed at a cell exactly while the simulator fills it with something in
range, a fallen tree or a van no receiver knows, and nowhere otherwise; nothing types anything at
runtime, since the slot is the obstacle and its cell is the one belief that changes.

# What a plan does with it

A world states, beside "no cell holds two vans", that no van stands where an obstacle is, a
`planning:Constraint` and not a desire (`domains/road/constraints.ttl`, held by each world's agents). The search marks every possible
world that puts the van on the obstacle's cell impossible, so a plan goes round it, and a slot filled
while a plan is walking is a belief that makes the plan's next world impossible, which reopens it
(#921). In the layby's tests a tree on the direct way to the parcel sends the van round through the
next column, two drives longer, and the tree is believed nowhere again once the van is more than two
cells from it.

An obstacle that moves is a seam the boat record leaves open: its cell is believed where it was last
seen, and a drifting one is a flow nobody has written.

---
type: Domain Concept
title: Adjacency
term: http://example.org/orexis/courier#adjacentTo
description: >-
  Which cells a drive can take a van between - `courier:adjacentTo`, from a cell to each cell a drive
  may reach from it, stated each way. A road states its edges itself, segment to segment and lane to
  passing place; a grid is a road where every neighbour is an edge, derived at onboarding from the
  coordinates into the world's `grid.derived.ttl`. The drive reads the edge and names no coordinate.
---

# What it is

A cell is where a van stands, and its coordinates are what a [position](/domain/courier/position.md)
fix and a [contact](/domain/courier/contact.md) report and the estimate measures a distance in; where a
van may DRIVE from it is a separate fact, `courier:adjacentTo`, one edge per direction. A grid lets a
van go anywhere, which is sand: every neighbour is an edge. A road lets it go where the road goes, or
pull in where there is somewhere to pull in: segment to segment, lane to passing place and back, and
nothing off the road. The drive's precondition reads the edge and nothing else, so the two geometries
differ in what writes the edges and not in the action.

# Who writes it

- **A road states its edges itself**, in the document that states its cells, since nothing can compute
  where a road goes. A world any of whose documents states an edge is a road, and is derived none.
- **A grid's edges are derived at onboarding** by `orexis-grid`, a step of `orexis-onboard`: every pair
  of the world's cells one apart, |dx| + |dy| = 1, each way, into `grid.derived.ttl` beside the world, a
  world graph every reader reads as the world's own. Committed, and held to a fresh derivation by
  `tests/test_layout.py`, as the society's topics are: what the coordinates imply is computed, never
  written by hand ([onboarding](/domain/onboarding/onboarding.md)).

The simulator reads the same edges and refuses a drive no edge leads along, as a road would. The
estimate stays the Manhattan distance, which on a road whose segments are grid-aligned never overstates
the drives still owed. This is the fourth section of
[navigation-is-a-body-a-mover-and-a-move](/decisions/navigation-is-a-body-a-mover-and-a-move.md)
built in the courier's words, for the grid and the road; a sphere's rule waits with the layer.

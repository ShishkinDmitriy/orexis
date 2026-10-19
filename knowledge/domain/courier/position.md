---
type: Domain Concept
title: Position
term: http://example.org/orexis/courier#Position
description: >-
  Where a van stands as an instrument observes it - a position fix hosted by the van reports the
  number of the cell it is on, each cell stating its number once, and the courier's one transition
  concludes `courier:at` of the number. A number no cell states concludes nothing, and a cell a fix
  reports is never posed.
---

# What it is

`courier:Position` is an observable property: a `sosa:Sensor` hosted by a van that observes it is the
van's **position fix**, reporting as its number the `courier:number` of the cell the van is on. An
instrument gives numbers and a cell is an IRI, so the world states each cell's number once, beside its
coordinates, and nothing else reads it: a search drives to cells and never to numbers, and where the
world answers a drive the van is told the number of the cell to reach
([driver](/domain/courier/driver.md), the two action documents).

# What the rules make of it

The courier's one [transition](/domain/belief/transition.md), `positionRule` in `rules.ttl`, is
triggered by the fix's percept arriving: it finds the cell that states the number, deletes the cell the
van was at and inserts the new one - the belief every drive's effect predicts, so a commanded drive lands
when the fix has shown it. The feature of interest is the van the fix is hosted by, or what a contact
`isSampleOf` where the fix is a receiver's (#1003). A number no cell states - an instrument's sentinel
beneath nought, a cell off the grid - concludes nothing and takes nothing away, so a van believed
somewhere stays there until a fix says where else.

**A cell a fix reports is never posed.** A transition changes the agent's DERIVED state alone, so a cell
asserted in a world's `state.ttl` would stand beside the one the fix concludes, the van on two cells and
its drive never answered (#1002, measured: every drive timed out). What comes from outside is stored when
it arrives: the lane poses its parcel's cell and its driver's van, and the van's cell is its first fix's
to say.

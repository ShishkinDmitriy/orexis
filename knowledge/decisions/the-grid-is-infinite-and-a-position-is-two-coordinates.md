---
type: Decision
title: The grid is infinite, a position is two coordinates on the thing, and the road is what the agent sees
status: accepted
timestamp: 2026-10-20T18:30:00Z
description: >-
  The sovereign, 2026-10-20 - the grid is infinite and an agent knows only part of it; do not author
  every cell, keep the coordinates of the van and of the obstacles, and give the agent an area it sees.
  Decided - `courier:Cell` and `courier:at` are retired. A position is `courier:x` and `courier:y` on
  the thing itself, a drive goes to any neighbour by arithmetic, a destination and a constraint are
  stated in coordinates, the road's shape is hedges the radar sees and not cells the world authors, and
  out of range is a vector outside the range the contact's sensors declare. A value an effect computes
  is reachable anywhere, so a constraint reading one couples everything and the reach is not asked.
  Refused - the cell as a node, a known map, a sentinel or a silence for out of range, and the reach
  over an unbounded domain.
---

# The question

#1013 left the road a domain of sixteen cells, each a node with two coordinates, and the lane and the
layby two worlds posed on it. The sovereign's remarks on it, in order: *every cell has x and y, we can
calculate adjacent, move north, move south - no need to generate links between them* (which closed
#1012); *the grid is infinite, but the agent knows only part of it*; and then *maybe we can not create
all the cells? Just have coordinates of van, and of obstacles. Agent has area that it sees.*

Each remark removes a layer the one before had left. A derived adjacency went first, since two
coordinates already say which cells are neighbours. The cells went next: once the grid is infinite, a
node per cell is a name for a pair of numbers, and sixteen of them are the sixteen pairs somebody chose
to write down. What remains is the question this record answers: what does a world author, what does an
agent know, and what does it see?

# What the tree held, verified 2026-10-20

- **A cell is a node and a position is a cell**: `courier:Cell` with `courier:x` and `courier:y`,
  `courier:at` from a van, a parcel, an obstacle or a peg to a cell, `courier:destination` to a cell, and
  the drive's precondition binding `?to a courier:Cell` one away from `?here`. The fix's transitions
  conclude the van's two coordinates and then, in `cellRule`, the cell authored at them, or nowhere.
- **The road's shape is which cells exist**: the lane is row 1 alone in columns 2 to 4 because no other
  cell is authored there, and a contact out of range is placed one past the far corner of the cells,
  where no cell is, which is how it came to be believed nowhere by geometry.
- **The simulator refuses a drive to a cell the world does not state**, and reads the cells for it.
- **A constraint's footprint is read over the reach** (`agent/planning/couplings.py`): the delete-free
  fixpoint of the effects over their preconditions, finite over the terms a store holds, closing in
  seven rounds on the courier's 4x4; two vans on disjoint grids were two wants because no reachable
  cell was both vans'.

# Decided

1. **A position is two coordinates on the thing.** `courier:x` and `courier:y` are what a van, a parcel,
   an obstacle, a peg and a destination carry; `courier:Cell` and `courier:at` are retired, and nothing
   stands between a thing and its coordinates. The fix's transitions conclude the van's coordinates and
   stop there; the cell rule, which found a node for them, goes. A parcel is at its destination when its
   two numbers equal the destination's two, which `courier:delivered` asks as a SPARQL constraint on the
   parcel; `courier:drivesOwed` is the Manhattan sum it already was, read off the things themselves.
2. **A drive goes to any neighbour, by arithmetic.** The precondition mints the four neighbours of the
   van's position, a `VALUES` of the four offsets and a `BIND`, and the drive takes the van and the two
   coordinates it drives to, `courier:toX` and `courier:toY`; the effect rewrites the van's two numbers,
   and the command carries them as it did. A pick takes a parcel whose coordinates are the van's; a drop
   writes the van's coordinates onto the parcel it carries, and takes the parcel alone.
3. **The road is what stands on it, and the agent sees it.** The lane's shape is hedges, obstacles the
   simulator poses where the cells were not - five things, not sixteen cells - and no agent is told
   them: it plans across the plane as if it were open, its radar sees a hedge within range, the slot is
   believed at the hedge's coordinates, the constraint makes the world the plan's next step lands in
   impossible, and the plan is reopened after the step in flight (#921). The road is discovered, not
   known. `domains/road/` is the hedges; the two constraints, stated in coordinates - no two vans at
   one pair, no van at an obstacle's pair - are the courier's own physics, `domains/courier/constraints.ttl`,
   which a world says who holds. The tower's yard is fenced the same way, obstacles its mover knows,
   since a move's want below carries no estimate and the fence bounds its search as nine cells did.
4. **The area an agent sees is the range its contact sensors declare.** Each sensor of a contact
   declares `ssn-system:MeasurementRange` with a least and a most offset; the simulator reports the
   true vector while the thing is inside both, and one past the most on each axis when it is not; the
   contact's transitions write a coordinate inside its range and delete one outside it, so a thing
   beyond range has no coordinates and is believed nowhere, by the range alone. `sim:radius` goes, the
   simulator reading the instrument's declaration as the agent does, one figure with one owner.
5. **A value an effect computes is reachable anywhere.** A drive's effect writes a number its
   precondition computed, and the reach over such an effect does not close: every round mints the next
   ring of coordinates, so the fixpoint is the guard, measured in millions of rows at sixty-four
   rounds. `couplings` reads the effects before it runs them: where a template value is one the
   precondition binds by an expression, the constraint reading that predicate couples everything, the
   safe side a constraint that will not run already takes, and no reach is run. On an infinite plane
   every two vans can meet, which is what that answers; the reach stays for worlds whose places are
   finite terms, hanoi's pegs. So there are no disjoint grids any more: one mind with two vans holds one
   want, however far apart they stand, and `world/driver/` and the derivation's cases say so.

# Refused

- **The cell as a node.** A node per cell was argued for as the thing a van is at, so that `courier:at`
  is one triple the effect rewrites and the met-test compares by `sh:equals`. But a cell has no fact
  but its two numbers, so every cell node is a second name for a pair the fix already reports, the
  world has to author every pair a van may ever reach, and the authored set becomes the map. Two
  triples per thing and a `FILTER NOT EXISTS` over them cost the met-test one SPARQL constraint where
  the shape compiler already compiles one.
- **A known map.** The road's cells, or hedges stated as beliefs the agent is given, would let the
  search find the detour before the van moves, and the lane's two tests were cheaper that way. Refused
  on the sovereign's words: the agent knows only part of the grid and sees an area. A plan that walks
  into what it could not see and is reopened when it sees it is the behaviour #921 built, and a map
  every agent is handed would never exercise it. The seam this leaves is a van that sees the hedge
  only one cell before it, a drive's band being forty-five seconds and the radar's range two cells: the
  radar's range, not the planner, is what a world widens.
- **A sentinel or a silence for out of range**, refused a second time (a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules):
  with no far corner to report past, a radar with nothing in range had to say something. A sentinel
  is a number the rules read specially, and a silence is a sensor sensing doubts. A vector outside the
  declared range is neither: SSN's own word for what an instrument can report, which the rules hold a
  reading to as the climate's hold a reading to a range.
- **The reach over an unbounded domain.** Bounding the rounds to a depth was weighed - a plan deeper
  than the budget allows is not found anyway - and refused, since a guard tied to nothing is a number
  somebody tunes, and the honest answer on a plane is that nothing is out of reach.

# Seams left open

- A refined want below carries no estimate, so its search is uniform-cost, and on an infinite grid a van
  seven steps from setting a disk down forks the plane in every direction: the tower's mover states a
  budget of 1024 where nine authored cells let 256 do. An estimate for a want the bridge mints - the
  courier's own, with `$this` bound to the disk - is where that cost would go, and nothing decides it here.
- The dispatcher's and the driver's figures grew with the four neighbours every world now opens, and are
  re-measured in their tests; the runbook keeps the day's numbers as history.
- A radar sees the nearest thing it does not identify, one per slot, so a van among several hedges
  believes one at a time and the believed obstacle moves as the slot retargets; a world that needs
  more seen at once carries more slots, as a ship carries more tracks.
- A hedge is an obstacle the radar sees, and nothing says a hedge from a van no receiver knows; a
  world that must tell them apart is where a second instrument saying what a contact IS would come
  from, the sovereign's own picture.
- The dispatcher's claims that rest on a cell - a joint plan sharing no cell, a parcel on a grid the
  walking van can never reach - are ported to coordinates where their premise survives and retired
  where it does not, ahead of the dispatcher's own retirement (#1004).

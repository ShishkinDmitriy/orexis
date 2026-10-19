---
type: Decision
title: Navigation is a layer - a body at a place, a mover aboard it, and a move the geometry admits
status: accepted
timestamp: 2026-10-19T14:00:00Z
description: >-
  The sovereign, 2026-10-19 - a generic ontology of moving, on a Cartesian grid, on a sphere by
  latitude and longitude, or along a road graph's edges; the mover a role, driver, skipper or pilot;
  navigation one layer and driving the one beneath it. Decided - navigation is a domain the courier
  imports. It says one thing, a BODY, and the move of it - a body is at a place, a mover is a role
  the world states an agent plays, aboard the body it moves, and a move takes the body to a place
  adjacent to the one it is at. A geometry is the one rule that concludes adjacency, and the grid is
  the only geometry built; the sphere and the graph are each that rule and an estimate. The helm, the
  engine and how a body gets to the next place are the driving layer, not built, and a move's command
  to the body is the seam it hangs on. Refused - vehicle, carrier, movable, thing and object as the
  word; a move per geometry; a domain per geometry; the hull level now; a public relation beside the
  role.
---

> **Parked 2026-10-19, the day it was decided**, until two minds meet on the van world (#922, #923):
> the layer and the nautical words wait on #1007 and #1008, and two pieces are taken now in the courier's
> words (#1002): §5's command to the body itself, a drive the world answers sent to the van and not to a
> helm, and §3's role, the driver an agent plays, stated by the world and carrying the vans it drives.
> **Decided 2026-10-19, and built by #1007 and #1008 in that order**, the second reworking what #1002
> built as the canal's helm. Until the first lands the tree speaks the courier's words, van, cell and
> driver, and the pages under `knowledge/domain/courier/` describe it as it is.

# The question

The canal (#1002) made a drive a command to a helm, and the sovereign asked why a helm, and then
whether the level a skipper plans at should know a helm or an engine at all: *abstract from the helm
and the engine on this level; have an agent with the role skipper, and this role brings the actions
for moving a boat; the helm and the engine are a level lower, as the tower is.* Then wider: *a
generic driving ontology, on Cartesian coordinates on a surface grid; another case is real latitude
and longitude on a sphere; another is a road, along a graph's edges. A mover is a role - driver,
skipper, pilot. Navigation is one layer and driving the second.*

And then the word for the thing that moves, by counter-example: *if I bring a package on foot, in my
hand, am I a vehicle?* A carrier was refused the same way: *what if I simply move a van without a
package? Navigation should describe something, and the move action of that something.* Thing and
object were weighed and set down for body.

# What the tree holds, verified 2026-10-19

- **The courier domain holds three things in one vocabulary** (`domains/courier/ontology.ttl`): the
  space - `courier:Cell` with `courier:x` and `courier:y`, and since #1002 `courier:number` and
  `courier:Position`; the moving - `courier:Van`, `courier:at`, `courier:Drive`, `courier:Driver`
  `aboard` a van, `courier:hasDriver` from the agent and `courier:drivenBy` from the van, the
  boarding in `driver.ttl`, and the helm; the delivery - `courier:Parcel`, `courier:destination`,
  `courier:carriedBy`, `courier:Pick`, `courier:Drop`, `courier:delivered` and `courier:drivesOwed`.
- **The geometry lives in two texts.** The drive's precondition works out that two cells are
  neighbours where |dx| + |dy| = 1 (`domains/courier/actions.ttl`), and the estimate measures a
  Manhattan distance off the same coordinates (`domains/courier/shapes.ttl`). Nothing else reads x or y.
- **A driver is a thing the agent HAS, not a role it plays.** #929 made `courier:hasDriver` the
  public relation a peer finds the agent by, drawn as the line between a role, internal, and a
  relation the world states
  ([a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md),
  §4). The role record since made a role an instance with a context, carrying what belongs to it,
  and said that a role a peer must address is stated in a document every agent of the world is given
  ([a-role-is-an-instance-an-agent-plays](/decisions/a-role-is-an-instance-an-agent-plays.md)). A van
  the world names no driver for is moved by the agent's own hand, which is every van of the tower's
  and the courier's worlds.
- **Four worlds pose the courier** - `world/courier/`, `world/driver/`, `world/tower/` with hanoi
  above it, and since #1002 the canal of its open PR read as boats, where `nautical:Boat` is beneath
  `courier:Van` and the drive is a command to a `courier:Helm`
  ([a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules](/decisions/a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules.md)).
- **The tower is the precedent for two layers**: hanoi's move above, the courier's drives below, and
  a step refined only where it would be fictive, its goal below the world it lands in
  ([refinement](/domain/planning/refinement.md)).

# The decision

## 1. Navigation is a domain, and the courier imports it

The space and the moving leave the courier for a domain of their own, navigation, and the courier
keeps the delivery: parcel, destination, pick, drop, delivered and the estimate. The nautical
vocabulary goes beneath navigation's classes where it named the courier's, so a boat is a body, a
berth a place and a skipper a mover, and beneath the courier's where it names the courier's, so a
cargo is still a parcel. The tower types a disk a parcel and its van a body. A word is one concept:
there is one `at`, one `aboard`, one move, and every world that moves something speaks them.

## 2. The thing is a body

**A body is what is at a place.** An empty van is a body. A person on foot is a body. An iceberg is
a body no move moves. A parcel is a body, at a place until a pick takes it aboard another; so the
courier needs no position relation of its own and `courier:carriedBy` folds into `aboard`, the one
relation for being in or on a body and going where it goes. Body names what has a position; moving
is what a mover does to one. The words weighed and refused are below.

## 3. A mover is a role, stated by the world

**A mover is a role an agent plays, aboard the body it moves.** The driver, the skipper and the
pilot are kinds of mover, each a domain's word for the role on its own ground. The role carries what
is its own, as a role does: which bodies it moves, the world's word and never moved, and which it is
aboard, the state a boarding rewrites. `courier:hasDriver` and `courier:drivenBy` go: the first is
the agent playing the role, `orexis:plays`, the kernel's word; the second is the role's context.

The world states it, in the document every agent is given, because a peer branches on it: the agent
to ask about a body in range is the one that plays the mover aboard it (#923). The role record foresaw
exactly this - a role a peer must address is stated in the society, one no peer reads in the self
graph - and the mover is the first role stated that way. It loads no package: what an agent runs it
declares in its self graph as before, a planner and an executor, and the mover is beneath
`orexis:Role` alone. So the line §4 of the package record drew, a role internal and a public relation
beside it, is kept in substance and dropped in form: what is public is still what a peer's plan
branches on, and it is a role rather than a relation beside one.

**Every body a move moves has a mover aboard.** The tower's and the courier's agents, which today move
their van by their own hand, play a mover aboard it. A van the world names no mover for is a body
nothing moves, which is what an iceberg is. The move's precondition is then one shape in every
world: the self plays a mover, the mover moves the body and is aboard it, the body is at a place,
and the place asked for is adjacent to it.

## 4. A move is one action, and a geometry is the rule that admits it

**Adjacency is a relation between places, concluded by the geometry.** The move reads one triple,
that the place it is asked for is adjacent to the one the body is at, and names no coordinate. What
writes that triple is the geometry's:

- **on a grid**, an inference rule concludes it from x and y where |dx| + |dy| = 1 - the interpreter
  knows the coordinates, so adjacency is computed and never asserted;
- **along a road**, the world asserts each edge, since nothing can compute it;
- **on a sphere**, a rule concludes it from latitude and longitude where one leg reaches.

A geometry is that rule and nothing else of the move's. The grid is the only geometry built: a type
with one member is a type to fold back, and no world sails on a sphere or drives a road. What the
record fixes is the shape of the seam, so that a second geometry is one rule and one estimate.

**A place's number and its position are navigation's.** What #1002 put in the courier - the number a
place goes by on an instrument, the property a fix observes, and the transition that concludes `at`
from a reported number - is about where a body is, not about what it carries.

## 5. Two layers, and the move's command is the seam between them

**Navigation is what a mover plans over**: places, bodies, moves. **Driving is how a body reaches the
next place** - a helm, an engine, a rudder, a heading - and nothing a mover's plan branches on, so it
is not built. The grower commands a dose and never models the valve; a mover commands a move and
never models the helm. Where a world answers moves, the move is a command to the body itself, the
way a dose is to the pump: the body listens on a topic, the payload is the number of the place to
reach, and the body's own fix shows the landing. Where nothing below answers, as in the tower, the
move is fictive. Two action documents, one per implementation, a world importing the one it poses,
as #1002 decided; the helm as a word, a class and a second device goes.

The driving layer, when a real hull exists, is the tower's shape: a move above refined by a plan
below, where the move would otherwise be fictive. A simulated body that lands on the place it is told
has no plan below, so there is nothing to refine.

# Why

- **The courier was three domains wearing one prefix**, and the sovereign's three geometries showed
  which seam ran through it: the space varies, the moving does not, and the delivery is a different
  thing again. A boat delivering cargo and a van delivering a parcel are one shape; a boat crossing
  water with nothing aboard is navigation alone.
- **Body is held to every instance of the concept.** Vehicle fell to the person on foot, carrier to
  the empty van, movable to the parcel, which is moved but by a pick. Body is what has a position,
  and the iceberg, the parcel and the empty van are all at a place.
- **A mover is anti-rigid and carries a context**, which is what the role record says a role is: an
  agent can stop being a boat's skipper, and which bodies it moves is its context, as the venue is a
  host's. Stated as a relation the agent HAS, that context lived in two words with one reader.
- **A geometry that is one rule is a geometry a world can import**; a geometry written into the
  move's text is a move per geometry, and three actions for one concept is the synonym the
  dictionary refuses.
- **Driving is below the derivative the mover controls.** A move's effect is the body at the next
  place; its size, its heading and its engine are the body's. Modelling them at the mover's level is
  the one move this architecture refuses, reaching down a level
  ([control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)).

# What was refused

- **Vehicle**, the first word. A vehicle is what one rides, and a person carrying a package on foot
  rides nothing. **Carrier** next: an empty van carries nothing and still moves. **Movable**: a parcel
  is movable too, and is moved by a pick, not a move, and an iceberg is at a place and moved by
  nothing. **Thing**: `owl:Thing` is every class's superclass and the bundle's own word for anything
  whatever, so a narrower `nav:Thing` is a second concept under the one word. **Object**: a triple
  has an object, a repository holds domain objects, and Python has a third; a `nav:Object` in a
  SPARQL text sits beside the object of its own pattern. **`sosa:Platform`** was offered, since the
  boat already hosts its fix: refused because a platform is what hosts an instrument, and an iceberg
  and a parcel host nothing and are still at a place.
- **A move per geometry.** A grid move, a graph move and a sphere move, each with its own
  precondition: the same action three times, each a whole declaration to keep in step.
- **A domain per geometry**, with the grid in a directory of its own beside navigation. One geometry
  exists; a directory for the one member is the fold-back rule's case. The grid's words live in
  navigation until a second geometry asks where they go.
- **The sphere and the road graph built now**, as cases with no world. The seam is what is fixed.
- **The hull level now** - an engine, a fix, a steer, a bridge rule to `at`, the canal searched on
  two levels. Nothing a mover plans branches on it, and a simulated body needs no plan below.
- **A public relation beside the role** - `hasMover`, agent to mover, as `hasDriver` was, with the
  role internal. Two words for one fact, held in agreement by onboarding, which is what the role
  record folded `market:hosts` to escape.
- **A cell as a class of its own beneath place.** A place with x and y is on the grid; a class
  saying so says nothing the coordinates do not.

# Seams left open

- **A second geometry.** The sphere's rule and the road's edges are each one rule; what each also
  needs is an estimate, since the courier's measures a distance off the grid's coordinates and SPARQL
  has no function a document can declare. A courier on a sphere ships its estimate beside the rule,
  and its desire points at it. The estimate is the one text the geometry cannot be hidden from.
- **A mover on foot.** A mover is aboard a body, and a person walking is a body with a mover aboard
  that is itself. The model admits it and no world poses it; the driver's boarding still says a mover
  is never between bodies on foot.
- **The driving layer.** When a world has a hull with a heading and a speed to choose, the move is
  refined by a plan below, as hanoi's is by the courier's. The sovereign's picture of it: navigation
  finds the path, and a domain for the van or the boat, imported beneath it, adds the specific
  actions - starting, steering, stopping - whose bridge rule concludes the body at the next place
  from what they change, which is all the refinement asks. The simulator's command and that plan
  below are one seam, a move that is not fictive at its own level. Nothing fixes the words of that
  layer.
- **An obstacle is a body**, and the contact (#1003) types a radar's slot one; whether a drifting
  obstacle is a flow stays the contact's seam.
- **A mover of several bodies at once** is the driver world's dispatcher, one mover boarding between
  two vans. Two movers one agent plays, each aboard its own body, is admitted by the model and posed
  by no world.

# What it supersedes and amends

- [a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules](/decisions/a-boat-is-a-van-and-a-contact-becomes-a-belief-by-the-rules.md),
  in part: a boat is a body and not a van, and the drive is a command to the body, not to a helm.
  The contact, the sentinel, the obstacle and the canal replacing the dispatcher stand.
- [a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md),
  §4, amended: the courier's public fact is a role the world states, not a relation beside one.
- [two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict](/decisions/two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict.md),
  the 2026-10-08 amendment: whom to ask is the agent that plays the mover aboard the body in range.
- #929's relation, `courier:hasDriver`, is retired with the issue's outcome kept: an agent's search
  moves its own bodies alone, and a peer is found by the mover.

# How it is built

Two issues, each a PR. **#1007, the navigation layer**: the domain with place, body, mover, `at`,
`aboard`, the move in two documents and the grid's adjacency rule; the courier reduced to the
delivery and importing it; the nautical words beneath both; the tower, the driver and the courier
worlds moved onto it with their outcomes and figures unchanged, each agent playing a mover; the
dictionary filed under a folder of its own and the courier's pages reduced to the delivery.
**#1008, the canal on it**: #1002's slice reworked - the move answered by the world as a command to
the boat, the simulator playing a body that moves on command, the helm gone - and the open PR for
#1002 closed in its favour. #1003 and #1004 then build on the canal as this record leaves it.

---
type: Decision
title: A boat is a van, a drive is answered by the world, and a contact's numbers become a belief by the rules
status: accepted
timestamp: 2026-10-19T09:00:00Z
description: >-
  The sovereign recast the two-minds world on 2026-10-18 as boats in a canal - a radar shows
  numbers, another instrument says what the contact is, and the rules turn both into "a boat at this
  cell"; an iceberg is a contact with nothing to discuss. Decided - the canal replaces the dispatcher
  as the world two minds meet in, and its boats are vans: a nautical vocabulary beneath the courier's,
  so the three actions and the driver apply unchanged. A drive becomes a command the simulator answers,
  since a radar needs true positions, and the one-agent worlds keep the fictive drive by importing a
  second action document. An AIS receiver per known vessel and a radar slot per unknown contact are
  ordinary numeric sensors reading a cell's number, and a courier transition concludes the cell;
  a sentinel number ends a contact that left range. Refused - a nautical domain with its own words,
  categorical readings in sensing, a contact list of variable length, and the dispatcher kept beside
  the canal.
---

> **Decided 2026-10-19, and built by #1002, #1003 and #1004 in that order.** Until they close, the two-minds world is the
> dispatcher, with the peer stood in by `_van_c` in its tests.

# The question

#922 asks for attention: a van senses the vans within a radius, by identity and cell, played by the
simulator from the true positions, so that a peer seen on a cell is a present fact the constraint keeps
the search out of, whatever was or was not said. Setting out to build it found two things in the way,
and the sovereign answered both with a picture from real life.

The first: there are no true positions. `courier:Drive` is `execution:Fictive` - each agent writes its
own van's cell into its own beliefs, and the simulator knows no van - so no sensor can be played from
positions that exist only inside two stores. The second: sensing is numeric end to end, a reading is a
float, and a sighting "van C on c2_1" is an identity and a cell.

The sovereign's answer: *we can see how boats in real life decide who goes first, and how they know it
is a boat in front. A radar just shows numbers; another sensor recognises what it is; and all those
numbers are converted by the belief revision into "boat at xxx". It could recognise an iceberg, and
there is nothing to discuss with it.* And the better example for this world is a boat with a radar, the
corridor a canal; the dispatcher is replaced with boats.

# What the tree holds, verified 2026-10-19

- **Drive, Pick, Drop and Board are fictive** (`domains/courier/actions.ttl`, `driver.ttl`): each
  writes its effect into the agent's own state when taken, and no command leaves the agent. The
  simulator (`simulation/simulator.py`) plays sensors with a `sim:Model` and answers two commands, a
  dose and a heating; it holds no position of anything.
- **Sensing reads one number per sensor at a JSON pointer** (`agent/sensing/pipeline.py`, `_number`),
  or an array of `{value, age_s}` readings of one sensor; a percept's result is `xsd:decimal`; the rules
  conclude what it is OF from what hosts the sensor (`ofRule`, `sosa:isHostedBy`), and the requirement
  alone follows a `sosa:Sample` to what it `isSampleOf`. A transition is handed its arrival and no
  other testimony, with the world and the agent's own derived state (#947, #944).
- **The dispatcher is one agent with two vans and no bus**, and its tests pin one mind's coupling,
  its waits, its reconsideration and the contradiction a posed collision is; a peer is stood in by
  writing a cell into the state or a belief ahead (`_van_c`). The driver world is one agent with two
  vans on two grids and a driver each van needs (#929).
- **The two-minds record names attention as sensing's and the courier as the first slice**, and
  leaves open the shared circuit as the second world, a peer that never speaks, and more than two
  vans in one radius.

# The decision

**The canal replaces the dispatcher as the world two minds meet in.** the canal world: two agents, a
boat each, on a grid of water cells - open water at both ends and a canal one cell wide between them
with one passing bay, the well-formed corridor the two-minds record demands - each boat with cargo
owed at the far end, so the two must pass. Each agent plays observer, predictor, planner and executor,
has its own skipper, holds the constraint that no cell holds two vessels, and knows of the other boat
only what its instruments say. The dispatcher's directory goes; what its tests pinned about one mind
- two parcels coupled into one want, the waits, the reconsideration after a step in flight, the posed
collision refused - is kept as one-agent VARIANTS of the canal, a world rewritten so one agent has both
skippers, as the dispatcher's tests already rewrote their world per case. The driver world stays as it
is.

**A boat is a van.** The courier domain already has the grid, the cell, `courier:at`, the parcel, the
driver and the three actions, and a boat on a canal is that shape on water. A nautical vocabulary
(`domains/nautical/`) declares `nautical:Boat rdfs:subClassOf courier:Van`, `nautical:Skipper
rdfs:subClassOf courier:Driver`, `nautical:Cargo rdfs:subClassOf courier:Parcel` and `nautical:Berth
rdfs:subClassOf courier:Cell` - the words the world reads as - and the closure makes every boat a van,
so Drive, Pick, Drop and Board, the driver's hold and the aversion to two vans on one cell apply
without a letter changed. One concept, one word: a boat is not a second concept beside a van, it is a
van the world calls a boat.

**A drive is answered by the world.** `courier:Drive` gains an `execution:Command` whose payload is the
destination cell's coordinates, sent to the boat's helm, a simulated actuator; the simulator moves the
boat over the drive's band and the boat's own position instrument shows the landing, so the step lands
when the world can show its effect, as a dose does, and the executor says only what happened. The
one-agent worlds keep the fictive drive: the courier ships two action documents, `actions.ttl` with the
fictive implementation and `actions.helm.ttl` with the commanded one, and a world imports the one it
means - the driver world the first, the canal the second. Two documents for one action, each a whole
declaration, rather than a flag a world sets on an action it does not own: a document says which graph
it is, and a world imports what it poses.

**A contact's numbers become a belief by the rules.** Two instruments per boat, both ordinary numeric
sensors the simulator plays from the true positions and the world binds to pointers in one message:

- **An AIS receiver, one sensor per known vessel.** Real AIS broadcasts a vessel's number, and a
  receiver demultiplexes by it; here the identity is the world's authored knowledge, each peer boat
  stating its `nautical:mmsi`, and the receiver's sensor for that number reads the peer's position as
  ONE number, the cell's `nautical:number`, which every cell of the canal states. Its feature of
  interest is a `sosa:Sample` hosted by the receiving boat and `isSampleOf` the peer boat, a contact
  standing for the vessel; the courier transition reads the arriving number, finds the cell that states
  it, and concludes `<peer> courier:at <cell>` in the agent's own state, superseding the cell before.
  Beyond the radius the receiver reports the sentinel `-1`, and the transition retracts the peer's cell:
  a boat that left range is believed nowhere, and the cell it stood on is free.
- **A radar, one sensor per contact slot.** A contact with no number is something the radar sees and
  nothing identifies - an iceberg. Each slot's sample stands for nothing the world names; the transition
  concludes `<slot> courier:at <cell>` and types the slot `nautical:Obstacle`, and the canal holds a
  second constraint, no vessel on an obstacle's cell. There is nothing to ask an iceberg, so #923's
  exchange never addresses one: a question goes to the agent that has the skipper of the boat in range,
  and a slot has none.

Both are one reading, one transition, one belief - the shape every sensor here already has - and the
whole of the fusion the sovereign described is the rules: numbers in, "boat at this cell" out, in the
agent's own state where the constraint reads it. Sensing learns nothing new.

**The radius is the world's**, stated on each instrument's `sim:Model` as the simulator's premise and
in the world's prose as the author's: it must cover one drive and a message's flight, as #922 says, and
the draw's two documents each way once #923 lands. The figure is measured where the canal is tested.

# Why

- **Real life is the model, and it is already numeric.** A radar gives ranges and bearings, AIS gives a
  number, a chart gives the cell, and the officer of the watch makes "a boat at that position" of them.
  Sensing kept numeric is sensing that reads what instruments give; the conversion the sovereign
  describes is belief revision's job and is what the transitions are for (#944).
- **A radar needs a world that moves.** With fictive drives the two agents' boats exist in two stores
  and nowhere else; a simulator playing a radar would have to read both, which rule 4 forbids. A drive
  the world answers is also the executor's own rule, that the world moves an intention and the executor
  says what happened, applied to the one action here that still wrote its own outcome.
- **One concept, one word.** Van, Parcel, Cell and Driver are the concepts; Boat, Cargo, Berth and
  Skipper are what one world calls them. A nautical domain restating the actions would be the synonym
  the dictionary refuses, and every fix to the courier would have to be made twice.
- **A corridor with a passing bay is the shape the convention is held to.** The two-minds record says
  decentralised prioritised planning is complete only where the world is well-formed; a canal with one
  bay is that world, and the dispatcher's grid was never a corridor.
- **An iceberg settles what a peer is.** A contact one can negotiate with is one that has an agent
  behind it, found by the skipper it has; a contact with none is an obstacle, avoided as a cell is
  avoided. The distinction the protocol needs falls out of the identity instrument, and nothing guesses.

# What was refused

- **A nautical domain with its own actions.** Steer, Load and Unload beside Drive, Pick and Drop: the
  same three concepts under second names, which `test_no_two_domain_pages_state_the_same_claim` and the
  rule above both refuse.
- **Categorical readings in sensing.** An observation whose result is an IRI, one per feature seen, with
  a rule mapping strings to cells: a second pipeline beside the numeric one, for an instrument that in
  life gives numbers. The cell's number and the transition do the same work in the words sensing has.
- **A contact list of variable length in one reading.** A radar document `{"contacts": [...]}` read by
  one sensor: a sensor observes one property of one feature, and a list of unknown length has no
  pointer. Slots, each a sample, are what a real radar's track table is.
- **Silence as "out of range".** A receiver that falls quiet beyond the radius would be doubted after a
  limit of cadences, and the peer's last cell would stand until then; a sentinel is a reading, read at
  once, and a silence stays what it is, a fault.
- **The dispatcher kept beside the canal.** Two worlds for one shape, the older one pinning what the
  newer must also hold; the pins move as variants and the directory goes.
- **A flag on Drive for whether it is commanded.** A world does not edit an action it does not own; it
  imports the document that declares the action it poses.

# Seams left open

- **A contact slot carries one vessel at a time.** Two unidentified contacts need two slots; how many
  the world declares is the author's, and a third contact in a two-slot radar is unseen.
- **An iceberg does not move.** The obstacle's cell is believed where it was last seen; a drifting
  obstacle is a flow nobody has written.
- **AIS is trusted.** A vessel that states another's number is believed to be it; a receiver that checks
  a claimed identity against the radar's contact is the first slice of trust between agents, parked with
  reputation.
- **Three boats in one radius**, as the two-minds record leaves it: the draw is between two.
- **The radius figure.** Stated by the world, measured by the canal's tests, and the draw's cost added
  when #923 lands.
- **The x and y of a cell are the cell's.** A boat's position is a cell's number, not coordinates; a
  world finer than its cells would need the position as two readings and a transition reading two
  states, which the order groups allow and nothing here needs yet.

# How it is built

Three issues, in order, each a PR: #1002, the helm - `actions.helm.ttl` with the commanded drive, the
simulator's boat that moves on command and reports its position, and a one-boat canal that drives;
#1003, the contact - the nautical vocabulary, the AIS receiver and the radar slots as samples, the
courier transition from a cell's number to `courier:at` and its retraction on the sentinel, the
obstacle and its constraint; #1004, two minds in the canal - the two-agent world with its bus, the
dispatcher's tests ported as one-agent variants, #922's test that a peer seen on a cell keeps the
other's plan out of it, and the dispatcher retired. #923 then runs on the canal.

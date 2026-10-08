---
type: Domain Concept
title: Driver
term: http://example.org/orexis/courier#hasDriver
description: >-
  Someone a van needs aboard to move, load or unload, and the agent whose it is - `courier:hasDriver`,
  agent to driver, public, stated by the world. A drive, a pick or a drop with a van somebody drives,
  and a boarding, are admitted only through a driver the agent has, so two agents in one world never
  act with each other's vans; and a peer is found as the agent that has the driver of the van in range.
---

# What a world states

```turtle
:dispatcher courier:hasDriver :driver .                  # whose the driver is: public, authored
:driver a courier:Driver .
:van_a a courier:Van ; courier:drivenBy :driver .        # which vans need it: authored, never moved
:driver courier:aboard :van_a .                          # where it is: state, rewritten by a boarding
```

Three facts about one driver, each with its own author and reader. `courier:drivenBy` and
`courier:hasDriver` are the world's and never move; `courier:aboard` is the agent's belief, and a
boarding rewrites it. The relation runs to the driver rather than to a van because a driver boards
another van, and what an agent can move goes with its driver.

# What the search does with it

Four actions read it, and they hold it two ways:

| action | what it asks of a van the world names a driver for |
|---|---|
| `courier:Drive` | the driver aboard that van, and the agent having the driver |
| `courier:Pick` | the same, of the van the parcel is loaded into |
| `courier:Drop` | the same, of the van carrying the parcel |
| `courier:Board` | the agent having the driver it moves |

The agent asking is found as `?me a orexis:Self`, as every text finds the
[self](/domain/kernel/self.md). The pick and the drop ask for the driver ABOARD and not only had
(#931), because the driver is the one body at a van's cell and is never on foot: a van it has left
stands where nobody is, and a pick or a drop there is what a drive there already was, an act with
nobody to take it. The boarding asks for no driver aboard the van it names, being the act that
changes which van that is. A van no driver is named for is driven, loaded and unloaded by the agent's own hand, as in the
courier's, the dispatcher's and the tower's worlds, which state no driver. A driver no agent has is
nobody's to act through, the same refusal as a driver aboard another van.

So in `world/driver/` the dispatcher reaches both vans because it has the one driver, one van at a
time; and in a world of two agents with a driver each, each search admits the drives, picks, drops
and boardings of its own driver and none of the other's — held by
`world/driver/tests/test_driver.py`. A [footprint](/domain/planning/footprint.md) reads the self as
absent, so a scope still sees every agent's driver; what narrows is the precondition, asked in each
possible world with the self in it.

# What a peer does with it

It is public because a peer needs it to address the agent. A van sensed in range (#922) leads to the
agent to ask (#923): the one that has the driver aboard that van. What an agent runs is its own and
no peer reads it; whom to ask is a relation the world states, as `market:hosts` is for a bidder
looking for the [host](/domain/market/host.md) of a venue
([a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md),
§4).

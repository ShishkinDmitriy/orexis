---
type: Role
title: Driver
term: http://example.org/orexis/courier#Driver
description: >-
  Someone a van needs aboard to move, load or unload - a role an agent plays, `orexis:plays`, stated
  by the world in the document every agent is given, carrying the vans it `drives` as its context and
  the van it is `aboard` as its state. A drive, a pick or a drop with a van somebody drives, and a
  boarding, are admitted only through a driver the agent plays, so two agents in one world never act
  with each other's vans; and a peer is found as the agent that plays the driver aboard the van in range.
---

# What a world states

```turtle
:dispatcher orexis:plays :driver .                       # whose the driver is: the role, public, authored
:driver a courier:Driver ; courier:drives :van_a , :van_b .   # which vans it may drive and board: its context
:driver courier:aboard :van_a .                          # where it is: state, rewritten by a boarding
```

Three facts about one driver, each with its own author and reader. The role and its context are the
world's and never move; `courier:aboard` is the agent's belief, and a boarding rewrites it. The driver
is a [role](/domain/kernel/role.md) because it is what the role record says a role is: anti-rigid, an
agent can stop being a van's driver; with a context, the vans it drives, as a host has its venue; and
reified, so that where it is aboard is a fact about the role and not about the agent. It is stated in
the world and not in the self graph because a peer branches on it, which the role record foresaw for a
role a peer must address; it loads no package, what the agent runs being its self graph's word, and the
boot reads roles for loading off the self graph alone. It was a relation the agent HAD, from #929
until #1002, and the one fact a peer reads is the same.

The actions themselves come in two documents, `actions.ttl` with the drive fictive and
`actions.answered.ttl` with it a command to the van itself, which the world answers and the van's
[position](/domain/courier/position.md) fix shows; a world imports the one it poses (#1002).

# What the search does with it

Four actions read it, and they hold it two ways:

| action | what it asks of a van the world names a driver for |
|---|---|
| `courier:Drive` | the driver aboard that van, and the agent playing the driver |
| `courier:Pick` | the same, of the van the parcel is loaded into |
| `courier:Drop` | the same, of the van carrying the parcel |
| `courier:Board` | the agent playing the driver it moves, into a van the driver drives |

The agent asking is found as `?me a orexis:Self`, as every text finds the
[self](/domain/kernel/self.md). The pick and the drop ask for the driver ABOARD and not only played
(#931), because the driver is the one body at a van's cell and is never on foot: a van it has left
stands where nobody is, and a pick or a drop there is what a drive there already was, an act with
nobody to take it. The boarding asks for no driver aboard the van it names, being the act that
changes which van that is. A van no driver drives is driven, loaded and unloaded by the agent's own
hand, as in the courier's, the dispatcher's and the tower's worlds, which state no driver. A driver no
agent plays is nobody's to act through, the same refusal as a driver aboard another van.

So in `world/driver/` the dispatcher reaches both vans because it plays the one driver, one van at a
time; in `world/lane/` each courier plays the driver of its own van; and in a world of two agents with
a driver each, each search admits the drives, picks, drops and boardings of its own driver and none
of the other's - held by `world/driver/tests/test_driver.py`. A
[footprint](/domain/planning/footprint.md) reads the self as absent, so a scope still sees every
agent's driver; what narrows is the precondition, asked in each possible world with the self in it.

# What a peer does with it

It is public because a peer needs it to address the agent. A van sensed in range (#922) leads to the
agent to ask (#923): the one that plays the driver aboard that van. What an agent runs is its own and
no peer reads it; whom to ask is a role the world states, as `market:hosts` is for a bidder looking
for the [host](/domain/market/host.md) of a venue
([a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md),
§4, as amended).

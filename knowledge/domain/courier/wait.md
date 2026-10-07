---
type: Domain Concept
title: Wait
description: >-
  The courier's action that keeps a van on its cell for a stretch, so a plan can let another van
  clear a cell rather than drive round it. Its effect takes the van's cell away and puts the same
  cell back; a step of it is a world of its own only where it lands in a later ground. Shipped in
  `domains/courier/wait.ttl`, which a world imports when it has something to wait for.
---

# What a wait is

`courier:Wait` is an [action](/domain/kernel/action.md) of the courier domain taking one van: the
van stays on its cell for half a minute to a minute, at a cost of one, as a drive is costed and
banded. A drive changes where a van is; a wait changes when it gets anywhere. It is fictive, as
every courier action is, and a van somebody drives waits only with them aboard, as it drives.

It is what a plan needs where another van's route crosses its own and is known ahead, laid as a
[prediction](/domain/prediction/prediction.md): a van whose next cell the other is due to stand on
can stand still until that cell is clear. On the dispatcher's grid with the other van driving down
the third column, the plan is a drive, a wait, two drives and the drop; without a wait the van drives
back a cell and returns, six steps
([measure-the-search](/runbooks/measure-the-search.md), `world/dispatcher/tests/test_dispatcher.py`).

# Its effect rewrites the van's own cell

The delete takes the van's `courier:at` away and the construct, asked of the same world before either
is applied, puts the same cell back ([effect](/domain/planning/effect.md)). The van does not move,
which is the point, and the search still sees a change, since it forks for a delete. An effect
stating nothing would not do: the search makes no world for a step whose effect comes to nothing,
and an action stating no effect falls in no [scope](/domain/planning/scope.md), so no search would
admit a wait at all.

# A wait is a world of its own only across a ground

A step's world is forked from the ground holding at its earliest landing. In the ground the wait is
taken in, its world holds what its parent holds, hashes the same, and is passed over as a repeat —
so where nothing is predicted to move, a wait costs a fork and buys nothing. Where its landing falls
in a later ground, a prediction has moved something there, the other van has driven on, and the
wait's world is new. A plan therefore waits for a prediction, never for the clock: two waits inside
one ground are one world, and a stretch longer than a wait's least landing with nothing predicted
to change inside it cannot be waited out.

# Where it lives

In a document of its own, an `orexis:ActionGraph` the courier's ontology does not import, so a world
asks for it beside the ontology as `world/driver/` asks for the boarding. Every world importing it
admits a wait per van in every world its search opens, and pays a fork for each: imported by the
shipped dispatcher, the joint search spends 296 candidates for the same ten steps where it spent
228, past the budget its tests state. No shipped world imports it; the dispatcher's test poses the
crossing in a variant that does.

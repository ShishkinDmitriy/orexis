---
type: Decision
title: A fork copies the half a pass can touch, and the other half is set aside
description: >-
  A search node copied the whole of the agent's readings whatever its step changed, so a fork
  was O(state) and a padded world spent 65% of its pass forking. A pass now sets aside the
  readings its view names nothing of, into one graph read with the invariant half — disjoint,
  so no reader pays a subtraction and no rule text learns precedence. Refused by measurement,
  twice - a node's graph holding only what its path changed, because hanoi and the courier read
  untouched subjects inside `GRAPH $state`, and a reading narrowed to the subject the agent
  acts for, because the vent reads the outside's air.
status: accepted
timestamp: 2026-09-15T22:30:00Z
---

# A fork copies the half a pass can touch

`Imaginarium.reached` makes a node's world by copying its parent's readings and applying the
step's diff. That is the right shape — it is what makes a step's baseline the previous step's
conclusion — and its cost is O(state) per node against O(1) in the size of the change.
[a-node-holds-one-world](/decisions/a-node-holds-one-world.md) measured that, said plainly
that it is a limit rather than a property, and named the number to watch: **the size of the
mutable slice**. This is the change that shrinks it.

Measured on a 3-disk hanoi solve — 50 forks, seven moves — with the state graph padded out
with facts no action writes:

| padding | mutable half | fork | share of the pass | and after |
|---|---|---|---|---|
| none | 3 quads | 7.6 ms | 1.0 % | 1.1 % |
| 100 | 103 | 25.5 ms | 8.5 % | **2.8 %** |
| 1,000 | 1,003 | 202 ms | 34.8 % | **2.6 %** |
| 5,000 | 5,003 | 1,027 ms | 57.9 % | **1.6 %** |

The mutable half stays at 3 quads in every row: what a fork copies no longer moves with what
the agent happens to hold.

# What is set aside, and why that is the bound

**The want's VIEW, which the pass already computes.** `_compiled.view` is the predicates the
want's relevance closure names — what the want reads, plus what every relevant lever reads
*and* writes — and `_project` is the one test of whether a fact is in it. A subject of the
readings with nothing in the view is a subject no rule of this pass can bind, so moving it out
of the world a rule is asked about changes no answer. `Imaginarium.divide` moves those subjects
into one graph, and the planner reads it with the invariant half from there on.

**Reads must not pay for it, and they do not.** The two halves are DISJOINT: a fact is in one
graph or the other, never in both. A reader that merges graphs — the compiled met-test, the
legality check, the border text — simply names one graph more, and every pattern reads both
with no precedence to establish. That is what separates this from the overlay
[a-node-holds-one-world](/decisions/a-node-holds-one-world.md) refused, whose whole cost was
that *the newest value wins* has to be said in the rule text, by every package, for ever. A
rule scoped to `GRAPH $state` reads the mutable half alone, which is exactly what the view
promises it may need.

**Where relevance knows nothing, nothing is set aside.** A want whose closure reaches a text no
parser can name answers `ANYTHING`, there is no view, and the world stays whole — the same safe
direction over-approximation takes everywhere else here.

# The two narrower readings, and the measurements that refused them

## A node's graph holding only what its path changed

The tempting one, and the one the issue was filed on: a path of depth d has changed at most d
subjects, so a node could hold those and read every other subject from the invariant half —
O(depth) rather than O(subjects). `_Node.changed` already tracks exactly that set.

**Refused, because a rule reads more than its step changes.** Hanoi's Move walks
`?s (hanoi:on)+ ?about` inside `GRAPH $state`, over a tower no step of the path has touched;
the courier's Pick reads `?about courier:at ?cell . ?via courier:at ?cell`, which is every
parcel and every van. A basic graph pattern under one `GRAPH` clause matches entirely within
one graph, so a subject the node's graph does not hold is a subject that pattern silently fails
on. What may be set aside is bounded by what a rule may READ, and the path's own changes say
nothing about that.

This is also why the split is per PASS and not per node: the view is the desire's, it does not
move while the pass runs, and one division at the root serves every fork under it.

## A reading narrowed to the subject the agent acts for

The other half of the issue's claim: a dose changes one pot's moisture, not all five hundred,
so a reading of the property the want is about could be kept only where its key names the
subject this agent acts for — the one instance the kernel already carries into every rule as
`$subject`. Built, and it took a padded loner world from 25,008 mutable quads to 8.

**Refused by the greenhouse.** `climate:Venting` reads the OUTSIDE's air inside `GRAPH $state`,
because without it nothing says which way opening the vent would move the bed — and the outside
is nobody's subject. With its reading set aside, the vent's construct bound nothing, the cold
night stopped being refused, and the suite said so. Reaching the other way is no better: every
pot an agent polls is linked to it through `sensing:polls`, which a look's own precondition
reads, so a closure from the agent keeps all five hundred anyway.

**So the narrowing is by property, not by subject**, and that is the predicate-level limit
[measure-the-search](/runbooks/measure-the-search.md) already recorded when scopes were
measured — *a scope of PREDICATES cannot separate two vans, which needs a variable, a subject
and a predicate together*. Telling this pot's reading from that one is the same mechanism as
telling two vans apart, and it belongs where that work is.

Measured on `world/loner`, one pass, forking twice, with the state padded by extra subjects:

| padded with | mutable half before | after |
|---|---|---|
| 5,000 readings of another property | 25,008 quads | **8** |
| 5,000 readings of the property the want is about | 25,008 | 25,008 |

# What moved besides the fork

**The levers passed over are asked of the belief base.** They are the levers this pass finds
IRRELEVANT, so their preconditions read precisely what the view left out; asked of the
imaginarium they would bind nothing and the trace would say a row had vanished rather than that
it was passed over. The root's readings ARE the agent's own — at the root and again at every
re-root, where the present is observed from that very store — so it is the same world it always
asked, and a whole one.

**A prediction about a place the pass cannot touch is not overlaid.** The search stands a
prediction's node in for the reading a world holds by replacing that node in the world's own
graph. Where the reading was set aside, the replacement would land beside it rather than over
it: one key, two readings, and a want judged on whichever came back first. A place no rule
reads is a place no measure asks about, so the overlay skips it.

**A step that reaches outside the view says so.** It cannot happen — the view holds every
predicate a relevant lever writes — and a quiet version of it would break the disjointness the
whole design rests on, so `_reaches_aside` logs the places by name. No shipped world triggers it.

# Seams left open

- **The invariant half is divided again on every re-root**, from nothing, because the present is
  observed and what was set aside may have moved with it. That is O(state) once per re-root
  against O(state) per fork, so it is the right trade at every size measured here — and it is
  still linear in a thing that does not change.
- **The pass itself is still linear in the readings the agent holds**, and the fork is no longer
  the reason. On the padded loner world a pass costs 18 s at 5,000 extra subjects with the fork
  at 7 ms of it: the flatten `_beliefs()` builds, the base facts, the border text and the
  entailment are what is left to measure.
- **Separating two subjects that carry the same predicates** is #565's first item and not this
  one's.

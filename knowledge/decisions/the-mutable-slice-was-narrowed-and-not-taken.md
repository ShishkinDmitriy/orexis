---
type: Decision
title: The mutable slice was narrowed, measured and not taken
description: >-
  A fork copies a node's whole world, so the plan was to shrink what a fork copies to the half
  a pass can touch. Built, and it works - a padded solve goes from 58% of its time forking to
  2%. Not taken, because the profile says the fork is 0.1% of a real pass and the narrowing
  buys that by adding an assumption, while the reads it does not touch are 15%. Two narrower
  readings were refused by worlds rather than by argument, and the finding that redirects the
  work is that a rule naming the world it reads is a package claiming something about every
  other package's actions.
status: accepted
timestamp: 2026-09-16T10:00:00Z
---

# The mutable slice was narrowed, measured and not taken

[a-node-holds-one-world](/decisions/a-node-holds-one-world.md) refused an overlay and named the
number to watch: **the size of the mutable slice**, since a fork copies a node's whole world and
that cost is O(state) against O(1) in the size of the change. This is the attempt to shrink it,
what it measured, and why the number to watch turned out to be a different one.

The mechanism: a pass sets aside, once at its root, every subject its **view** names nothing of
— the view being what the want reads plus what every relevant lever reads *and* writes — into
one graph read alongside public knowledge and the records. The halves stay disjoint, so a reader
that merges graphs names one graph more and no rule text learns precedence. It was built as
[PR #664](https://github.com/ShishkinDmitriy/orexis/pull/664), the whole suite passed on it, and
every shipped world planned exactly what it had planned.

# What it bought

A 3-disk hanoi solve — 50 forks, seven moves — with the state graph padded with facts no action
writes:

| padding | mutable half | fork share before | after |
|---|---|---|---|
| none | 3 quads | 1.0 % | 1.1 % |
| 100 | 103 → 3 | 8.5 % | **2.8 %** |
| 1,000 | 1,003 → 3 | 34.8 % | **2.6 %** |
| 5,000 | 5,003 → 3 | 57.9 % | **1.6 %** |

Flat in what the agent happens to hold, where it had been linear. On `world/loner` padded with
5,000 readings of a property the want does not name, 25,008 mutable quads become 8.

# Why it was not taken

**The fork is not where a pass spends its time.** Profiled after the narrowing, on
`world/loner` with 2,000 padded subjects:

```
whole pass                    6.11 s
  _begin                      4.94 s   (81%)
    the canonicaliser         3.25 s   (53%)
    relevance                 1.47 s
    the invariant signature   0.95 s
    the rdflib flatten        0.88 s
  forking, 50 nodes         ~ 0.007 s   (0.1%)
```

Every shipped world is smaller than that, and there the fork was already 1.0% (hanoi) to 0.0%
(the plant worlds). So the narrowing wins on padded worlds nobody has composed, and wins nothing
on the worlds that exist.

**And it is not free — it costs an assumption.** Setting a subject aside is only safe if no rule
of the pass can bind it, and the bound is *relevance never under-reports what an action reads*.
That holds today and it is not proved; it is the same class of claim as the ones this area keeps
getting wrong, and the penalty for being wrong is an empty result rather than an error. Checked
whether the risky half could be dropped and the saving kept: it cannot. Every reading carries
`sosa:hasFeatureOfInterest` and its neighbours, which `sensing:Observing` writes, so a partition
by predicate alone sets nothing aside — the whole saving comes from the clause that judges a
reading by its key. **The win and the risk are the same clause.**

# The two narrower readings, refused by worlds rather than by argument

## A node's graph holding only the places its path changed

O(depth) rather than O(subjects), and `_Node.changed` already holds the set. Refused because a
rule reads more than its step changes: `hanoi:Move` walks `?s (hanoi:on)+ ?about` inside
`GRAPH $state` over a tower no step has touched, and the courier's Pick reads
`?about courier:at ?cell . ?via courier:at ?cell`, which is every parcel and every van. A basic
graph pattern under one `GRAPH` clause matches entirely within one graph, so a subject the
node's graph does not hold is a subject that pattern silently fails on.

**What may be skipped is bounded by what a rule may READ, never by what a step changed.** That
is why the split had to be per pass rather than per node.

## A reading kept only for the subject the agent acts for

The other half of the proposal — a dose changes one pot's moisture, not all five hundred — using
the one instance the kernel already carries into every rule as `$subject`. Built, and it took a
padded `world/loner` from 25,008 mutable quads to 8.

Refused by the greenhouse. `climate:Venting` reads the OUTSIDE's air inside `GRAPH $state`,
because without it nothing says which way opening the vent would move the bed, and the outside
is nobody's subject; with its reading set aside the vent's construct bound nothing and a cold
night stopped being refused. Reaching the other way is no better — every pot an agent polls is
linked to it through `sensing:polls`, which a look's own precondition reads.

So the narrowing is by property and not by subject, which is the predicate-level limit
[measure-the-search](/runbooks/measure-the-search.md) already recorded when scopes were measured:
*a scope of PREDICATES cannot separate two vans, which needs a variable, a subject and a
predicate together.*

# The finding that redirects the work

Both refusals are the same fact seen twice: **a rule saying which world it reads is a package
making a claim about every other package's actions.**

`GRAPH $state { … }` means *a plan can change this, so read it from the world I am imagining*;
an unqualified pattern means *a plan cannot, so read whatever holds at this instant*. Which one
is right depends on the whole loaded set of actions, and a package author chooses from inside
one package — for actions that do not exist yet. It is the same shape as the rule this project
already enforces for derivations, *a premise may not rest on another package's conclusions*,
except that here the conclusions are a future package's.

The scar is in the tree. `climate:Venting` carries its own correction:

> **THE OUTSIDE IS NOT READ FROM `$state`, and that is the correction (#589).** A step changes
> the bed and never the weather…

"A step changes the bed and never the weather" is true only while no loaded action writes an
outside reading. Ship a shade, a fan, or a second grower venting into the same space, and the
vent reads the pre-plan value: no error, no empty result, a wrong plan.

**The fix belongs in the engine, not in a better guess.** A rule states what it needs to be true
and a layered dataset resolves it — the delta where the plan changed the fact, whatever holds at
that instant where it did not, which is right in both directions and makes #589's correction
something nobody has to know. Priced on this repo rather than inherited: engine reads are about
15% of a pass (111 ms of 760 ms on hanoi, against 8 ms of forking, a ratio of 14 to 1), so the
1.3x an overlay was once measured at is **2–5% of a pass**. That is cheap for removing a
cross-package claim, and it is a different trade from paying it to save a 0.1% fork.

# Seams left open

- **The overlay's real multiplier is unmeasured for this shape.** The 1.3x is from
  2026-09-01 and the shadowing needs two clauses per pattern, not one: subject shadowing covers
  Move and Pick, but a reading is retracted as one node and minted as another under the same
  key, so a keyed node needs a second clause carrying `orexis:keyedBy`.
- **A property path has no overlay form**, and precedence does not give it one — a transitive
  closure cannot alternate between two graphs. Materialising the shadowed extension of the
  path's own predicate is an escape hatch invisible to the author, and it costs what a fork
  costs when that predicate is most of the state, which is exactly hanoi.
- **A query spanning two stores** would remove the copy from the belief base into the
  imaginarium as well, and cannot be had in SPARQL — it is the same `spareval` trait one step
  further, and the copy is also what makes a pass a snapshot, so removing it is not purely a
  saving.
- **The branch stands** at `the-mutable-slice-was-narrowed-and-not-taken`'s sibling, PR #664,
  unmerged. If a world is ever composed whose agent holds hundreds of subjects and the overlay
  has not landed, it is there and it works.

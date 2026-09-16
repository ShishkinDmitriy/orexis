---
type: Decision
title: A rule does not say which world it reads
description: >-
  A rule wrote `GRAPH $state` for a fact a plan can change and an unqualified pattern for one
  it cannot — a choice that depends on the whole loaded action set, made by one package about
  every other package's actions, including packages that do not exist yet. The door is told
  which world now and the text names none; 48 wrappers came out of 11 files, five doubled
  clauses became one each, and the kernel's own class check lost a UNION. Refused with it -
  holding a node as a diff, which is a different change that had been coupled to this one.
status: accepted
timestamp: 2026-09-16T21:00:00Z
---

# A rule does not say which world it reads

Every rule in the tree used to make a choice, pattern by pattern:

```sparql
GRAPH $state { ?standing sosa:hasFeatureOfInterest $subject }   -- a plan can change this
?pot water:driesPerDay ?rate                                    -- a plan cannot
```

Which is right depends on **the whole loaded set of actions**, and the author choosing is
inside one package, writing for actions that may not exist yet. It is the shape of the rule
this project already enforces for derivations — *a premise may not rest on another package's
conclusions* — except that here the conclusions belong to a future package.

**The scar is in the tree.** `climate:Venting` carried its own correction:

> THE OUTSIDE IS NOT READ FROM `$state`, and that is the correction (#589). A step changes
> the bed and never the weather…

"A step changes the bed and never the weather" is true only while no loaded action writes an
outside reading. Ship a shade, a fan, or a second grower venting into the same space, and the
vent reads the pre-plan value: no error, no empty result, a wrong plan.

# What the door does instead

`Store.about(world, at)` assembles the graphs a rule is answered over — public knowledge, this
agent's own records, and **one world's readings standing where this agent's own stand**. An
actuator asking about the world it is in is handed its own; a search asking about a node is
handed that node's. The rule says only what it needs to be true.

Nothing overlaps, and that is what makes it free: the world named REPLACES the readings rather
than joining them, so there is one answer per fact and no precedence for anyone to establish.

`effects.apply`, `cost_of`, `lands_after`, `affordances_of`, `Store.query_at` and
`Store.construct` all take `world` and no longer take `$state`. `planner._bind` no longer
carries a graph at all.

# What it deleted

- **48 `GRAPH $state { … }` wrappers**, from 11 files across 8 packages.
- **Five doubled clauses.** `market:Offering` asked twice whether a round was open, once of
  what the host believes and once of the world a plan imagines; four debt rules asked twice
  whether a debt was discharged. One clause covers both now, and there is no second one to
  forget — forgetting it planned a second round, silently.
- **A UNION in the kernel's own class check.** `effects` built
  `{ ?v a ?t } UNION { GRAPH $state { ?v a ?t } }` because a type could be in either; the door
  merges them.
- **`ower._unmet`'s second `FILTER NOT EXISTS`**, and the keeper's `GRAPH $state` around a
  bridge's promise — which was the keeper stating, on the bridge's behalf, that a plan could
  change what the bridge translated.

# Measured: it costs nothing, and it wins nothing

Best of five per side, the two sides ALTERNATED in one session:

| | before | after |
|---|---|---|
| hanoi, 2 disks | 179.0 / 184.0 ms | 179.5 / 170.2 ms |
| hanoi, 3 disks | 306.1 / 320.8 ms | 318.6 / 303.7 ms |
| `world/loner`, dry pot | 1307 / 1348 ms | 1351 / 1313 ms |

Fork counts unchanged everywhere, and the times inside each other's noise. **A wash.**

This first said FASTER — 258 to 182 ms and 476 to 312 — and that was a measurement, not a
result. The two sides were timed in separate invocations minutes apart, and the bench machine
drifts about twofold between them, so what was read as an improvement was the machine cooling
off. **Alternate the sides within one session, or a number here says more about the Pi than
about the change.**

What IS measurable runs the other way, and is worth knowing rather than resolving: under
cProfile the engine's own time rose from 132 ms to 184 ms over the identical 669 queries,
because a pattern once scoped to one small named graph now reads the merged default graph. The
deletions evidently pay for that, since wall clock does not move — but "evidently" is as far as
these numbers carry, and the honest summary is that the contract cost nothing here.

# What was refused, and why it is a different change

The first attempt coupled this to **dropping the per-node copy** — a node holding only its diff,
with each pattern rewritten into *the adds, or the world where nothing was retracted*. That is
[PR #670](https://github.com/ShishkinDmitriy/orexis/pull/670), and it is real work: a SPARQL
scanner, a memo, an extension graph for property paths, and a parity gate that caught six
defects in it. It was refused here for three reasons, in order of weight:

- **It is not this change.** The author names no world either way. Dropping the copy buys
  nothing for the contract; it was coupled in because it won a per-node measurement.
- **It needs precedence, and precedence needs a rewriter.** Base and adds both hold the same
  key, so a read must prefer one — and a property path has no rewritten form at all, since a
  closure cannot alternate between two graphs. rdflib will not re-emit a CONSTRUCT
  (`translateAlgebra` returns empty), so the rewriter is ours to own.
- **The measurement stopped supporting it.** The fork is 0.1% of a pass; per-node it wins only
  past a few thousand triples of state, which is above every shipped world.

The branch stands if a world ever grows that far. What it proved on the way is kept: the fork's
copy is not where a pass spends its time, and a compiled violation select must be answered
about a world whole, because nobody authors it and its shape is a compiler's.

# Seams left open

- **A node still holds a copy of the readings.** That is the trade above, and the number to
  watch is in [measure-the-search](/runbooks/measure-the-search.md).
- **`$beliefs` is the same leak, smaller.** A rule still says `GRAPH $beliefs { … }` for the
  agent's own settings. That one is LOCAL knowledge — a package knows whether it is reading a
  belief of its own — so it is ergonomics rather than a claim about anyone else.
- **A world holding two readings on one key still scores arbitrarily** (#669). Nothing holds a
  world to one reading per key except each effect's own `orexis:retracts`.

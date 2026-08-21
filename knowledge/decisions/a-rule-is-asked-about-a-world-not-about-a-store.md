---
type: Decision
title: A rule is asked about a world, not about a store
description: >-
  Depth beyond one is nominal because a means' effect runs its CONSTRUCTs against the STORE, so
  the second step never sees what the first added. Measured what the rules actually read, and
  the answer decides it: every shipped effect reads exactly ONE mutable graph, `$sensed`, and
  `$sensed` is already a substituted parameter — so no rule changes. Run them against a SECOND
  pyoxigraph store, in memory for the life of one plan, with one named graph per search node
  because the frontier holds siblings at once. About 7 ms a plan against a 200-500 ms pass. An
  rdflib version of this was written first and refused by measurement: 163x slower per query,
  which would have tripled a pass on the Pi to save twenty thousand triples of memory.
status: accepted
timestamp: 2026-08-21T12:00:00Z
---

# The contradiction

A plan is `(beliefs − retracts) + adds` applied step after step. `agent/effects.py` computes
each step honestly and then computes the next one from the wrong place:

```python
added, retracted = apply(store, means, **bind)   # asks the STORE
world = copy_of(base)                            # applies to the HYPOTHESIS
```

So the first step is right and every step after it is wrong. The retraction re-asks the store,
finds the observation that is still stored, and never sees what the previous step added to the
world. Measured on the gardener: after two doses the world holds `0.08` beside `0.12` on one
deterministic observation node, and the reader takes whichever it finds. The second dose is
computed correctly and thrown away by cycle detection as somewhere already seen.

**Depth beyond 1 is therefore nominal for any goal about a measured value**, which is most of
them. `domain/deliberation.md` says so, and `a-plan-is-a-path-of-graph-diffs` recorded it as one
of the two limits found by building.

# What the rules actually read, which is what decides it

[#254](https://github.com/ShishkinDmitriy/agora/issues/254) offered two shapes and said that
choosing between them is the work. It is, and the choice falls out of a measurement neither
option assumed. Every shipped effect rule, by the graphs its two queries touch:

| rule | its `sh:construct` reads | its `ag:retracts` reads |
|---|---|---|
| `sensing:ObserveEffect` | `$sensed` | `$sensed` |
| `actuation:ActuateEffect` | the world graph, `$beliefs` | `$sensed` |
| `market:AcquireEffect` | the world graph, `$beliefs` | `$sensed` |

**Exactly one graph they read is mutable under a plan, and it is the same one every time.** The
world graph is authored and derived at genesis; beliefs are the agent's and no plan step writes
one. A plan moves readings, and only readings.

And the second half: **`$sensed` is already a parameter.** The rules say `GRAPH $sensed { … }`
and `_bind` fills it with the sensed graph's IRI, exactly as it fills `$me` and `$litres`. The
rules already ask about *whichever graph they are pointed at*. Nothing about them is bound to
the store; that is an accident of what the caller passes.

# The decision

**Run a rule against a second pyoxigraph store, held in memory for the life of one plan, with
each node's own readings in a graph of its own.**

At the start of a plan, copy the graphs a rule may read but no step may change — world, derived,
entailed, beliefs — into a fresh `pyoxigraph.Store()` with no path, which is in memory and is
not the belief base — the agent's **imaginarium**, in the sovereign's word, and the word is
better than a description because it says the thing that matters: what is in it never happened. Each node of the search then owns **one named graph** in that store,
holding the readings that node's world reached, and a rule evaluated at that node has `$sensed`
bound to that node's graph name. The rule runs unchanged, sees the world the previous step
reached, and its retraction finds the reading the previous step predicted rather than the one on
disk.

Nothing is written to the agent's own store, which is the property that mattered: a possible
world still cannot escape into somewhere that keeps things, because the store it lives in is
discarded with the plan.

## One graph per NODE, and not one mutable graph

The obvious reading of the paragraph above is a single hypothesis graph that each step
overwrites. That is wrong, and it is wrong in a way worth stating because it is the first thing
anyone will try.

**Planning is a search over a tree of states, and the states are alive at the same time.** The
search is breadth-first — `frontier` holds every node at a depth, `nxt` collects their children
— so siblings coexist rather than being visited one after another. A single mutable graph would
need save/restore around every expansion, and not even a stack discipline would serve, because
the frontier is a set rather than a path. Backtracking is not the hard case; *branching* is.

So a world is a VALUE, one named graph per node, written once when the node is created and
never mutated. Choosing another branch is binding `$sensed` to another name. There is nothing
to restore because nothing was disturbed.

The tree is bounded and small: `MAX_DEPTH` is 2 and a plant's menu offers two rows, so the
worst case is seven live worlds. That bound is the search's, not this design's — the same seven
worlds exist today.

## How the tree is held: paths, which are already there

The search does not need a tree structure added to it, and that is worth saying because the
obvious next step is to build one.

**A node already carries its path from the root.** `_Node.taken` is the ordered tuple of
affordance rows applied to reach it, and a child is `parent.taken + (row,)`. There are no parent
pointers and none are wanted: the frontier is one depth's worth of nodes, expansion produces the
next, and the path is the only ancestry anything asks about. What this design adds is a NAME per
node, and the path is what names it — deterministic, and it reads back in the trace beside the
`ag:through` a candidate already records.

**Fork, do not replay.** A node's graph is made by copying its parent's and applying the step's
diff — 0.19 ms, against a hypothesis of five triples. The alternative is to keep only paths and
recompute a world by replaying from the root whenever one is needed, which sounds cheaper and is
the shape of the bug: replay is exactly what `_world_of` does today, and it re-runs each step's
rule against the store rather than against the world the previous step reached. Materialising
per node is what makes a step's baseline the previous step's conclusion instead of the stored
reading.

`_world_of` therefore has the same defect as the search loop, at the end rather than during: it
rebuilds the chosen plan's world for the legality check, and past step one it rebuilds the wrong
one. Both call sites move together or neither is fixed.

**Nothing is cleaned up per node.** The imaginarium is discarded whole when the plan ends, so a
node's graph has no lifecycle of its own and no step has to remember to drop one. That falls out
of the store being separate, and it is most of why separate is the right call rather than a
temporary graph in the agent's own store: a crash mid-plan leaves nothing behind to find.

**Cycle detection stays keyed on the WORLD, never on the name.** `seen` holds signatures — the
rounded value the goal is about — and it is global across the search rather than per branch, so
two different paths that arrive at the same value collide and the second is pruned. Naming
graphs after paths must not quietly turn that into per-branch detection: two names, one world,
still one entry in `seen`.

## What it costs, measured

On `world/simulation`, per plan:

| | |
|---|---|
| load the invariant graphs into the in-memory store | **1.45 ms** (486 quads) |
| fork one node's readings into its own graph | 0.19 ms × 7 nodes |
| run a rule's CONSTRUCT | 0.32 ms × 14 |
| **a whole plan** | **≈ 7 ms** |
| a whole plan today, giving wrong answers past step one | ≈ 4 ms |
| a whole deliberation pass, for scale (#268) | 200–500 ms |

Three milliseconds on a pass that costs two hundred, to make depth 2 mean what it says.

**Load only the graphs a rule reads.** The whole store is 3,266 quads and takes 25.8 ms to copy;
the graphs rules actually read are 486 and take 1.45. The table above is the second number, and
the difference is large enough that it is part of the decision rather than an optimisation to
consider later.

## Why not the other two

**Not a diff layered over the store**, where reads fall through unless the hypothesis covers
them. The subtlety in "unless it covers them" is not a detail of the implementation, it *is*
the bug: two readings on one node is precisely a fall-through that went wrong. A design whose
central mechanism is the failure mode it must prevent needs a reason to be chosen, and there
is none here — it exists to avoid a copy that measurement shows is cheap.

**Not a new contract for the effects layer.** The issue proposed that `agent/effects.py` gain
the ability to execute a rule over an arbitrary graph, and asked what happens to a rule that
legitimately needs the world graph or a belief. The table above answers it: they all do, and
none of them needs a *changed* one. So the layer does not need a second mode. It needs to be
handed a different dataset.

# What this replaces, and the measurement that replaced it

**The first version of this record chose an rdflib dataset**, on the reasoning that
`world_after` already builds rdflib graphs and pyshacl already reads them, so the planning path
was rdflib's anyway. It stated the cost as a second SPARQL engine reading one query text — the
hazard [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md) exists to name —
and proposed to pay it with a both-engines test.

The sovereign asked whether a triplestore would not be easier on the Pi. It is, by two orders of
magnitude, and the design was refused by its own numbers:

| the same CONSTRUCT, the same data | |
|---|---|
| pyoxigraph | **0.27 ms** |
| rdflib | **43.59 ms** — 163× slower |
| snapshot store → rdflib dataset | 132 ms per plan |
| **a plan on rdflib** | **≈ 742 ms** |

A deliberation pass costs 200–500 ms. The rdflib design would have roughly tripled it, per agent
per tick, on a four-core Pi — to buy a memory saving of about twenty thousand triples, which is
nothing. **It measured the cheap axis and ignored the expensive one.**

Keeping pyoxigraph does not merely avoid that. It deletes the cost the first version was
budgeting for: with one engine there is no second engine to disagree with, so the both-engines
test that design owed is not owed by this one. The hazard was self-inflicted.

# Seams left open

- **A node's world is read by two things that want different shapes, and now two engines.**
  Rules want named graphs in the in-memory pyoxigraph store; `_met_in` runs pyshacl and
  `_urgency_in` reads a value, and both want one flat rdflib graph. So a node becomes a pair —
  the shared invariant snapshot and its own readings — and the flat rdflib view is materialised
  from that pair when validation asks for it. That materialisation is the piece of work this
  design does not remove, and it is why this is a change to what a possible world IS rather than
  only to which store a query runs against. It is also where the rdflib cost reappears, bounded:
  pyshacl was always going to run on rdflib, and it already does today.
- **A plan that moves something other than a reading.** The table is true of the three rules
  that exist, not of rules in general — an effect that wrote an intention or a belief would add
  a second mutable graph, and the snapshot would have to make that one replaceable too. The
  shape generalises (any graph a step may change moves from the invariant half to the
  replaceable half); the current implementation need not, and should not pretend to until a
  second such rule exists.
- **Depth is still bounded by the menu, not by this.** Fixing the baseline makes depth 2 honest;
  it does not make depth 3 useful. What limits a search is whether the levers compose, which is
  `the-ladder-of-means`' question and not this one.
- **The snapshot is per plan, so a plan cannot see a reading that arrives mid-search.** That is
  correct — a hypothesis explored against a moving world is not a hypothesis — but it means a
  long search plans against a world that has aged. The keeper's patience already bounds how
  long that can be, and nothing measures it yet.
- **`_world_of` moves with the search loop or neither is fixed.** It replays the chosen plan to
  check the world's legality and re-runs each rule against the store, so past step one it
  validates a world the plan would not reach. Named here because it is the same defect in a
  second place, and a fix that reached only the search would leave the legality check wrong.
- **Nothing here fixes cycle detection's signature.**
  [#258](https://github.com/ShishkinDmitriy/agora/issues/258) asks where a plan *is* using a
  number only some plans move; a correct baseline makes that question answerable rather than
  answering it.

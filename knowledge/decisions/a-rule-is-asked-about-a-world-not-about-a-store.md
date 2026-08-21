---
type: Decision
title: A rule is asked about a world, not about a store
description: >-
  Depth beyond one is nominal because a means' effect runs its CONSTRUCTs against the STORE, so
  the second step never sees what the first added. Measured what the rules actually read, and
  the answer decides it: every shipped effect reads exactly ONE mutable graph, `$sensed`, and
  `$sensed` is already a substituted parameter — so the rules need no change and the engine
  needs no diff layer. Run them against a per-plan snapshot of the invariant graphs, with each
  search node's own readings bound in as `$sensed` — one graph per node, because the frontier
  holds siblings at once. It copies less than the search does today, not more. The
  cost is that effect queries move from pyoxigraph to rdflib, which is a second engine reading
  the same text, and that cost is paid with the same guard one-graph-both-engines-read used.
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

**Run a rule against a per-plan snapshot, with each node's own readings bound in as `$sensed`.**

At the start of a plan, copy the graphs a rule may read but no step may change — world, derived,
entailed, ontology, beliefs — into one rdflib dataset. That is the invariant part, and it is
shared by the whole search. Each node of the search then owns **one named graph** in that same
dataset, holding the readings that node's world reached, and a rule evaluated at that node has
`$sensed` bound to that node's graph name. The rule runs unchanged, sees the world the previous
step reached, and its retraction finds the reading the previous step predicted rather than the
one on disk.

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

## Which makes it cheaper than what happens now

The bound above is why the invariant/mutable split is worth making, and the measurement is
lopsided enough to be the argument on its own. On `world/simulation`:

| | triples |
|---|---|
| the store | 3,261 |
| a node's world **today**, copied per node | 3,044 |
| the sensed graph — **the only part a plan step changes** | **5** |
| copied per plan today (7 nodes) | 21,308 |
| copied per plan if only the readings are per-node | **35**, plus one shared snapshot |

Today `_world_after` copies the entire belief base into a fresh `rdflib.Graph` for every node,
because a world is one flat graph and there is nothing in it that says which part a step could
have changed. Separating the invariant bulk from the five triples that move is not a cost this
design pays; it is a cost it stops paying.

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

# The cost, stated plainly

**Effect queries move from pyoxigraph to rdflib**, because the snapshot is an rdflib dataset.
That is a second engine reading the same query text, which is the hazard
[one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md) exists to name. This
project has already been bitten from the other direction — pyoxigraph binds nothing for
`duration / duration`, and a column computed that way read empty with no test going red.

It is a real cost and it is bounded, for two reasons. rdflib is already in the planning path:
`world_after` builds rdflib graphs today, and `_met_in` runs pyshacl over them. And the fix is
the one this project already knows — the guard, not the hope. **A test runs every shipped rule
on both engines against one graph and fails if the answers differ.** That is
`one-graph-both-engines-read`'s move applied to effects rather than to entailment, and it is
what makes the second engine safe to introduce rather than merely convenient.

# Seams left open

- **A node's world is read by two things that want different shapes.** Rules want a dataset
  whose `$sensed` is separable; `_met_in` runs pyshacl and `_urgency_in` reads a value, and both
  want one flat graph. So a node becomes a pair — the shared invariant snapshot and its own
  readings — with the flat view being their union. That union is cheap to take and it is a real
  piece of work, not a detail: it is why this is a change to what a possible world IS and not
  only to which dataset a query runs against.
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
- **Nothing here fixes cycle detection's signature.**
  [#258](https://github.com/ShishkinDmitriy/agora/issues/258) asks where a plan *is* using a
  number only some plans move; a correct baseline makes that question answerable rather than
  answering it.

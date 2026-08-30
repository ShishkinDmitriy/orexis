---
type: Decision
title: A rule is asked about a world, not about a store
description: >-
  Depth beyond one is nominal because a means' effect runs its CONSTRUCTs against the STORE, so
  the second step never sees what the first added. Measured what the rules actually read, and
  the answer decides it: every shipped effect reads exactly ONE mutable graph, `$sensed`, and
  `$sensed` is already a substituted parameter — so no rule changes. Run them against a SECOND
  pyoxigraph store, in memory for the life of one plan, with one named graph per search node
  because the frontier holds siblings at once. About 11 ms a plan against a pass costing over a
  second, and building it corrected two of the numbers below. An rdflib version of this was
  written first and refused by measurement: 163x slower per query, which would have tripled a
  pass on the Pi to save twenty thousand triples of memory.
status: accepted
timestamp: 2026-08-21T12:00:00Z
---

# The contradiction

A plan is `(beliefs − retracts) + adds` applied step after step. `packages/orexis-deliberation-search/effects.py` computes
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
them. `domain/deliberator.md` says so, and `a-plan-is-a-path-of-graph-diffs` recorded it as one
of the two limits found by building.

# What the rules actually read, which is what decides it

[#254](https://github.com/ShishkinDmitriy/orexis/issues/254) offered two shapes and said that
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

At the start of a plan, copy the graphs a rule may read but no step may change — every PUBLIC
graph, this agent's beliefs, and its readings (see *what building it corrected*, below: the four
this record first named are not enough, and the shortfall is silent) — into a fresh
`pyoxigraph.Store()` with no path, which is in memory and is not the belief base — the agent's **imaginarium**, in the sovereign's word, and the word is
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

It moved by being DELETED, which the argument above should have predicted and did not. If a
world is materialised per node, the node that wins is already holding the world the plan would
reach — so the legality check takes it as an argument and rebuilds nothing. `_world_of` existed
only because a node's world was thrown away when the search returned, and the reason given for
throwing it away was about the `Plan` (a possible world must not ride out to the ask channel on
a record that crosses module boundaries), which an argument does not do.

**Nothing is cleaned up per node.** The imaginarium is discarded whole when the plan ends, so a
node's graph has no lifecycle of its own and no step has to remember to drop one. That falls out
of the store being separate, and it is most of why separate is the right call rather than a
temporary graph in the agent's own store: a crash mid-plan leaves nothing behind to find.

**Cycle detection stays keyed on the WORLD, never on the name.** `seen` holds signatures — since
[#258](https://github.com/ShishkinDmitriy/orexis/issues/258), each world's net diff against the
base in canonical facts — and it is global across the search rather than per branch, so two
different paths that arrive at the same world collide and the second is pruned. Naming
graphs after paths must not quietly turn that into per-branch detection: two names, one world,
still one entry in `seen`.

## The imaginarium is not the intention ledger, and they must not converge

Both hold things that have not happened, which is enough of a resemblance to be worth refusing
in writing before someone tidies them together.

An **intention** is a commitment: `ag:IntentionGraph`, per agent, with an adoption, a resolution
and a reason, and it MUST survive a restart — a keeper that forgot what it had committed to
would re-adopt what already stands, and the patience that makes an intention an amortised
deliberation would amortise nothing. A **possible world** is `ag:PossibleGraph`, and it must
never survive anything: it is a conclusion drawn from beliefs plus an effect, so keeping one
would be keeping something that can outlive what it was concluded from.

They are opposites on the axis that matters. The intention ledger is the most durable thing an
agent writes; the imaginarium is the only thing in the design that is *required* to be lost.
That is why the imaginarium is a store rather than a graph in the agent's own: a graph can be
forgotten to be dropped, and a store that was never on disk cannot be.

## What it costs, measured

Re-measured on the Pi against what was built, because the estimate below it was wrong in one
place by a factor of seven — see *what building it corrected*:

| | `world/loner` | `world/simulation` |
|---|---|---|
| build the imaginarium | **10.4 ms** (2,646 quads) | **13.3 ms** (3,131 quads) |
| fork one node's readings into its own graph | 0.09 ms × 7 nodes | |
| run one rule (construct + retract) | 0.80 ms × 14 | |
| **the imaginarium's whole share of a plan** | **≈ 11 ms** | ≈ 14 ms |
| a whole deliberation pass, holding it | ≈ 1,100 ms | ≈ 1,100 ms |
| the same pass before this, at depth 1 with the wrong answer | ≈ 1,400 ms | |

**One percent of a pass, to make depth 2 mean what it says.** The pass is dominated by pySHACL —
`_met_in` is 0.083 s per candidate and depth 2 weighs roughly twice as many — and the two
figures above are close enough on this machine that the honest claim is *no measurable cost*
rather than a speedup, even though the deleted `_world_of` replay genuinely removed work.

The estimate this replaces read 1.45 ms for 486 quads and ≈ 7 ms a plan, against a pass of
200–500 ms. Both halves moved: the copy is larger because it has to be, and the pass is longer
because it is finally doing two steps.

## Why not the other two

**Not a diff layered over the store**, where reads fall through unless the hypothesis covers
them. The subtlety in "unless it covers them" is not a detail of the implementation, it *is*
the bug: two readings on one node is precisely a fall-through that went wrong. A design whose
central mechanism is the failure mode it must prevent needs a reason to be chosen, and there
is none here — it exists to avoid a copy that measurement shows is cheap (10–13 ms against a
pass over a second, once the copy is the size it actually has to be).

**Not a new contract for the effects layer.** The issue proposed that `packages/orexis-deliberation-search/effects.py` gain
the ability to execute a rule over an arbitrary graph, and asked what happens to a rule that
legitimately needs the world graph or a belief. The table above answers it: they all do, and
none of them needs a *changed* one. So the layer does not need a second mode. It needs to be
handed a different dataset.

# What building it corrected

Two claims above were measured wrong and one thing was missed entirely. They are here rather
than edited away, because the shape of both mistakes is the shape this project keeps meeting:
**a query that reaches somewhere nothing put anything returns an empty result, not an error.**

## The lean snapshot binds nothing

The record said to copy world, derived, entailed and beliefs — 486 quads, 1.45 ms — on the
reasoning that those are the graphs the shipped rules read, and made the smallness part of the
decision. It is not enough. Both the dose and the bid walk `?term market:ofGood ?good`, and a
valuation term is stated in a package's `ontology.ttl`, so it lands in the **ontology graph**
along with the T-Box. Copy the lean set and the CONSTRUCT binds nothing at all: no rows, no
error, no test going red — a planner that quietly finds every lever useless.

So the imaginarium copies **every public graph**, asked rather than listed, plus the private
graphs it is named: this agent's beliefs and its readings. That is 2,646 quads and 10.4 ms on
`world/loner` rather than 486 and 1.45. It is also the rule the rest of the repo already
follows — `store.public_graphs()` asks the vocabulary which graphs are public, and enumerating
four of them by hand is the same move [who-put-the-fact-there](/decisions/who-put-the-fact-there.md)
forbids for exactly this failure.

The table in *what the rules actually read* is still true as far as it goes. What it got wrong
was the inference from it: the rules read one MUTABLE graph, which is the load-bearing fact and
still holds, but the immutable half is not four graphs a person can enumerate — it is public
knowledge, whatever that currently consists of.

## Depth was 1 for a second reason, and it hid the first — and the fix was to delete, not to add

The contradiction at the top of this record says the second dose "is computed correctly and
thrown away by cycle detection". It was not computed at all. `MAX_DEPTH` is 2 and the frontier
was empty at every depth, because of an unrelated defect in how the search decides a step may be
followed:

> **A SENSING ACTION ENDS A PLAN.** A world with no violations means "nothing I can foresee is
> wrong", so a step chosen after a look was chosen against a value nobody has seen.

The search enforced that by asking `ag:confirmedBy ag:ByObservation` — and every effect in this
project answers exactly that. A dose is confirmed by observation; so is a bid; only a later
reading says the water arrived. So the guard matched every lever, nothing was ever added to the
next depth, and the search ran at depth 1 whatever the constant said. It was invisible because
the only thing that would have noticed is a correct second step, which the defect above
prevented — two bugs each hiding the other's symptom.

**The first fix was a truer term — `ag:changes ag:WhatIsTrue` against `ag:WhatIsKnown` — and it
was refused, correctly, by the sovereign asking whether it was needed at all.** It is not. An
action states a precondition, an implementation and an EFFECT; a plan is a path through world
space; and what a look does is something its effect already says, since it predicts the value it
found. The world it reaches therefore carries its parent's signature and the cycle check
discards it — the same road a zero-size bid arrives at "this does not help" by, which
`market:AcquireEffect`'s own comment was already arguing for.

Measured with the guard deleted outright, on three worlds including a first look with nothing
sensed at all: Observe is pruned as *a world already reached*, every time, and depth 2 works.
**A second statement of a fact the effect settles is a fact that can disagree with it** — which
is the argument this project makes everywhere else about capabilities being deduced rather than
hand-declared, arriving at a means. So the guard is gone and no vocabulary was added.

What that rests on is stated where it can be seen to break.
[#258](https://github.com/ShishkinDmitriy/orexis/issues/258) made the signature the world's net
diff in canonical facts, and in canonical form a look nets to nothing: an observation is its
upsert key and its value, never its `sosa:resultTime`, and a valueless first look states no fact
at all — see `packages/orexis-deliberation-search/signature.py`. A signature that counted a fresher timestamp as
somewhere new would make "look, then look" a new world every time. Chaining past a look
becomes a live question exactly there and nowhere earlier — the trigger, written down.

## The seams held

Everything else the record committed to survived contact. `$sensed` needed no rule change; one
graph per node was the right shape and a single mutable graph would have been wrong for the
reason given; cycle detection stayed keyed on the world; the flat rdflib view is materialised
per node exactly as the seam predicted, and that is still the piece of work this design does not
remove.

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
- **One query reads one store, so this pattern does not generalise to derived facts.** The
  obvious next thought is that if a planning store can be in memory, so could the derived and
  entailed graphs — they are a function of the files and nothing durable depends on them
  surviving. Measured, the case is stronger than it sounds: `refresh_public` rebuilds them on
  every start, and **98% of an agent's store is rebuilt every boot** — 3,196 triples of
  ontology, world, constraint, provenance, effects and both entailed graphs against 65 that are
  genuinely the agent's. Persisting them costs 175 ms a boot instead of 66, and 2.4 MiB of
  volume.

  It does not follow, because **pyoxigraph has no in-process federation**: `SERVICE` requires a
  URI scheme and is remote, and `default_graph`/`named_graphs` scope within one store. Derived
  facts in a second store would be invisible to every query that reads them.

  **The split the queries would actually permit is by graph family, and it is cleaner than
  splitting by persistence.** The sovereign's observation, measured: of 145 shipped query
  blocks, 140 read public knowledge alone, three name one private graph beside it, and
  **exactly one joins private graphs at all** — `desire/goals.rq`, over instruments, owed and
  sensed. Beliefs, intentions, obligations, summaries, revisions and evidence are never selected
  together. The silos are real, and a store per family would need a join across stores for about
  four queries out of a hundred and forty-five.

  **And the split would buy correctness, not only speed, which is the better argument.** The
  modality axis says a graph's TYPE is what its contents assert — is, would like, could do,
  doing, did — and the types do not overlap. A store per type makes that structural: the store
  answers *what modality is this* and the named graphs inside it keep answering *whose is it
  and how did it arrive*, which is the two-axis split
  [the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) already draws.

  It is violated today, in exactly one place, and it is already filed as
  [#264](https://github.com/ShishkinDmitriy/orexis/issues/264): `sensing:aims` is a WANT and it lives
  in `graph/beliefs/<agent>`, beside `patienceS`, `fastSleepS` and `maxValuePerL`, which are
  settings. Under a store per modality that triple could not be written at all — an aim is not a
  belief and there would be nowhere to put it. A defect becomes an unrepresentable state, which
  is worth more than the 109 ms.

  The desire store is the case that shows the shape working. `ag:ConstraintGraph` is deliberately
  a CLASS rather than one graph, and its comment says why — *"desire may have more than one
  source and a reader must not have to know how many"* — so one store would hold the sovereign's
  ratified mandate, the regions deduced from the world's ranges, and the obligations received on other
  agents' claims, as three graphs distinguished by `ag:arrivedBy`. Every reader still matches an
  unqualified pattern and sees all three, exactly as it does now.

  So this is blocked by a missing engine feature rather than by the design, and that is the
  useful thing to have written down. **The trigger for revisiting is local federation** — a
  SPARQL engine that can join two in-process stores, whether pyoxigraph grows one or something
  else is adopted. Until then the alternative is the whole store in memory with the durable 2%
  mirrored to disk, which buys 109 ms of boot and 2.4 MiB and costs a write-through path on
  every belief write whose failure mode is a belief that reaches memory and not disk. Beliefs
  are authored once and never touched, so that is the kind of loss nobody notices for weeks.
  Not worth it for that price; worth doing at the price local federation would charge.

  The imaginarium works *because* it needs no federation: it is a whole store, self-contained,
  and every query about a possible world is asked of it alone.
- **`$sensed` is bound by text and has to be.** pyoxigraph 0.5's `query()` takes a
  `substitutions` argument, which looks like the native binding `packages/orexis-deliberation-search/effects.py` says it would
  prefer. It is not: it pre-binds variables in the SELECT projection and cannot substitute a
  GRAPH name. The text substitution stays, and the comment saying so stays true.
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
- ~~**`_world_of` moves with the search loop or neither is fixed.**~~ CLOSED, and not the way
  this predicted: it moved by being deleted. Once a world is materialised per node, the node
  that won is holding the world the plan would reach, so the legality check takes it as an
  argument and replays nothing. A seam that turns out to be one line of the design's own logic
  is worth leaving visible rather than editing away.
- ~~**Nothing here fixes cycle detection's signature.**~~ CLOSED by
  [#258](https://github.com/ShishkinDmitriy/orexis/issues/258): the signature is the world's net
  diff against the base, in canonical facts, so a step that moves something other than the
  goal's number — a claim acquired, stock transferred — is somewhere new rather than a false
  cycle. The correct baseline this record built is exactly what made that answerable.

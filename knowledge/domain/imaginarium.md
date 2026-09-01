---
type: Repository
title: Imaginarium
description: >-
  The store a plan thinks in — a second pyoxigraph store, in memory for the life of one plan,
  holding the graphs a rule may read plus one named graph per node of the search. It exists
  because a SPARQL query reads ONE store, so "what would be true here" is answerable only if
  there is a store in which *here* is what is true; without it a step's retraction re-asked
  the belief base, found the observation still on disk, and depth beyond one was nominal. A
  world is a VALUE — one graph per node, written once, never mutated — because the search
  holds a whole open list of siblings at once, so branching rather than backtracking is the
  hard case. Nothing in it ever reaches the belief base, and it is discarded whole when the
  pass ends: it is the one thing in this design REQUIRED to be lost.
---

# What it is

`packages/orexis-agent-deliberation/imaginarium.py`. A subclass of the ordinary [belief base](/domain/belief-base.md) `Store`,
constructed with **no path** — so it is memory, and it is not the agent's. Into it go the graphs
a rule may read but no step may change, and out of it comes one named graph per node of a
planning search.

The word is the sovereign's, and it is better than a description because it says the thing that
matters: **what is in it never happened.**

# Why a second store at all

A plan is `(beliefs − retracts) + adds` applied step after step, and every step's rule is a pair
of SPARQL CONSTRUCTs. **A query reads one store.** So the question *what would be true here* is
answerable only if there is a store in which *here* is what is true — and there was not. The
effects layer computed each step honestly and asked the belief base for the next one:

```python
added, retracted = apply(store, means, **bind)   # asked the STORE
world = copy_of(base)                            # applied to the HYPOTHESIS
```

The retraction re-asked the belief base, found the observation still sitting on disk, and never
saw what the previous step added. The second dose's predicted reading landed *beside* the first's
instead of replacing it — two `sosa:hasSimpleResult` on one node, the reader taking whichever it
found. Depth beyond one was nominal for any desire about a measured value, which is most of them.
See [a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md).

**No rule changed to fix it.** `$sensed` was already a substituted parameter, and every shipped
effect reads exactly one mutable graph — so the rules already asked about *whichever graph they
were pointed at*. Being bound to the store was an accident of what the caller passed.

# What it holds

| | |
|---|---|
| every **public** graph | asked via `store.public_graphs()`, never listed |
| the agent's **beliefs** | where a prediction's conversion comes from |
| the agent's **readings** | the root node's own graph |
| one graph per **node** | `…/graph/possible/<path>`, forked from its parent |

**Every public graph, and the reason is a measurement.** The design record budgeted for four —
world, derived, entailed, beliefs — as "the graphs rules actually read". They are not: the dose
and the bid both walk `?term market:ofGood ?good`, and a valuation term is stated in a package's
`ontology.ttl`, so it lands in the ontology graph beside the T-Box. With the lean set the
CONSTRUCTs bind **nothing** — no rows, no exception, no red test, and a planner that quietly
finds every lever useless. Enumerating four graphs by name was also the move rule 1 forbids
everywhere else.

# One graph per NODE, not one mutable graph

The obvious reading is a single hypothesis graph each step overwrites. It is wrong, and it is the
first thing anyone will try.

**Planning is a search over a tree of states, and the states are alive at the same time.** The
search is best-first — one open list holds every node not yet expanded, whatever its depth —
so siblings coexist rather than being visited one after another. A single mutable graph would
need save/restore around every expansion, and not even a stack discipline would serve, because
the frontier is a set rather than a path. **Backtracking is not the hard case; branching is.**

So a world is a VALUE: written once when the node is created, never mutated, and choosing another
branch is binding `$sensed` to another name. There is nothing to restore because nothing was
disturbed.

**Fork, do not replay.** A node's graph is its parent's copied with the step's diff applied —
0.09 ms. Recomputing a world by replaying from the root sounds cheaper and is the shape of the
bug: a rule re-run has to be re-run against *something*, and that something was the store. The
legality check used to do exactly that, and past step one it validated a world the plan would not
reach; it does not replay now, because the node that won is already holding that world.

**Nothing is cleaned up per node.** The store is dropped whole when the pass ends — in a
`finally`, so a pass that raises leaves nothing behind either.

# It is not the intention ledger, and they must not converge

Both hold things that have not happened, which is enough of a resemblance to be worth refusing in
writing before someone tidies them together.

An [intention](/domain/intention.md) is a commitment, and it MUST survive a restart — a keeper
that forgot what it had committed to would re-adopt what already stands. A possible world must
survive **nothing**: it is a conclusion drawn from beliefs plus an effect, so keeping one would be
keeping something that can outlive what it was concluded from.

They are opposites on the axis that matters. The intention ledger is the most durable thing an
agent writes; the imaginarium is the only thing in the design *required* to be lost. That is why
it is a store rather than a graph in the agent's own: **a graph can be forgotten to be dropped,
and a store that was never on disk cannot be.**

# What it costs

Measured on the Pi, per plan:

| | `world/loner` | `world/simulation` |
|---|---|---|
| build it | 10.4 ms (2,646 quads) | 13.3 ms (3,131 quads) |
| fork one node | 0.09 ms × 7 nodes | |
| run one rule (construct + retract) | 0.80 ms × 14 | |
| **its whole share of a plan** | **≈ 11 ms** | ≈ 14 ms |
| a whole deliberation pass, holding it | ≈ 1,100 ms | ≈ 1,100 ms |

About one percent of a pass, which is dominated by pySHACL. An rdflib version was written first
and refused by measurement — 43.59 ms per CONSTRUCT against pyoxigraph's 0.27, 163× — which would
have tripled a pass on a four-core Pi to save twenty thousand triples of memory.

# The seam it does not close

A node's world is read by two things that want different shapes, and now two engines. Rules want
named graphs in the imaginarium; the desire check runs pySHACL and wants one flat rdflib graph. So a
node is a **pair** — the shared invariant snapshot and its own readings — and the flat view is
materialised from that pair. That materialisation is the piece of work this design does not
remove, and it is where the rdflib cost reappears, bounded: pySHACL was always going to run on
rdflib.

# Related

- [belief-base](/domain/belief-base.md) — the store this one is copied from and never writes to.
- [deliberation](/domain/deliberator.md) — the search that builds one per plan, and what a means'
  effect rule is.
- [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) — why a possible
  world is a diff over beliefs rather than a state of its own.

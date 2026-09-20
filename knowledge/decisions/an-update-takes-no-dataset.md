---
type: Decision
title: An update takes no dataset, so the derivation may become rules and the search may not
description: >-
  Asked why an agent reads objects out of its store and writes them back when a graph store
  has no schema and a derivation is an INSERT WHERE. The round-trip is smaller than it looks
  - a repository here is four selects and a dataclass - and the Python that matters chooses
  rather than copies. Measured against the engine, one thing separates the two. A query is
  handed its dataset per call, which is how a reader hands a query the graphs of the kinds
  it means holding at an instant; an update names its graphs only in its own text. So the derivation, whose
  every step is a function of the data, may become two updates once the scope partition and
  the view per instant are materialised as graphs; the search, whose every step is a choice
  - an order, a budget, a stop - may not, and was refused. The line is stated once - a rule
  for what is a function of the data, Python where a dataset is chosen or an order is - and
  a derivation written as rules keeps the loud select in front of the silent insert.
status: accepted
timestamp: 2026-09-18T20:00:00Z
---

# The question

Asked by the sovereign after the ledger stopped minting wants
([one-function-mints-every-want](/decisions/one-function-mints-every-want.md)): why read objects
out of the triple store into Python and move them back? A relational store limits a writer to
its schema; a graph store does not, and a derivation is an `INSERT … WHERE` — new nodes and
links from the ones there. Could one update mint the wants under a desire? Could one update fork
a possible world by applying an action to it? Do the repositories need to exist at all, or are
they rule executors that happen to hold a dataclass in the middle?

# Where the round-trip is, and how small

`Wants` is four selects and a `Want`; `mint` is three selects and a `save`, which is itself an
update. That is a few milliseconds and a few dozen lines, and nothing here defends it. The
Python that matters does not copy, it CHOOSES: which graphs are the world at the
instant a witness is read (the door,
[a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md)),
which witnesses one action could move together (the [scope](/domain/scope.md) partition,
a union-find in `relevance.scopes` memoised on the agent), what the choir answers for
`orexis:foresight` — a question since deleted — and what time it is. A repository is not what the question is about; a
repository is a NAME for a collection
([a-repository-is-named-for-what-it-holds](/decisions/a-repository-is-named-for-what-it-holds.md)),
not a claim that an object must exist between a read and a write.

# What an update can do, and the one thing it cannot

Measured against pyoxigraph 0.5.9, which is the engine every agent runs:

- `Store.query` takes `default_graph=[…]` **per call**. That is the dataset: the reader asks
  `graphs_of` for the graphs of the kinds it means holding at `at` and hands the list to
  `query`, which hands it to the engine. A rule text never learns which graphs it read (#666).
- `Store.update` takes **no dataset**. An update names graphs only inside its own text —
  `WITH`, `USING`, `GRAPH` — and a pattern inside one `GRAPH` clause matches entirely within
  that graph, which is the trap the door exists to keep out of rule text: the doubled clauses
  and the `UNION` that #666 deleted.

Everything else the derivation does is expressible. A want's name is `IRI(CONCAT(…))`; the instant
it holds at is `MIN(?at)` per cluster; what it is about is `GROUP_CONCAT(STR(?about))` (over
the IRI it binds nothing — the trap AGENTS.md records); what already stands is
`FILTER NOT EXISTS { ?w prov:wasDerivedFrom ?root ; orexis:about ?a }`; the label, the points
copied from the root, the period from the keeper's patience are all reads of the same store.
The dataset is a parameter of a query and a constant of an update, and that is the whole
difference.

# The derivation may become two updates, on two conditions

**The scope partition is data.** It is a function of the actions loaded and the edges their
rules read, neither of which changes while the agent runs; today it is recomputed in Python
whenever the memo is dropped, which is every write. Materialised at genesis as a triple per
predicate saying which scope it is in, clustering is a `GROUP BY`.

**The view per instant is a graph.** The door, as data: for each prediction's start, one update
copies every graph holding at that instant into one view graph. The whole compiled body of the
desire's met-test then sits inside ONE `GRAPH ?view { … }` — a view is one graph, so the trap
does not bite, and the select the compiler emits is unchanged. A copy per instant is what a fork
already does; forking was measured at a tenth of a percent of a pass
([the-mutable-slice-was-narrowed-and-not-taken](/decisions/the-mutable-slice-was-narrowed-and-not-taken.md)).

With both, the derivation is two updates and no Python object: the views, then one
`INSERT { the want } WHERE { SELECT ?scope ?instance (MIN(?at)) (GROUP_CONCAT(STR(?about))) …
GROUP BY ?scope ?instance }` with `$now` and the instants bound in by the same binder every
rule takes its tokens through. What stays in Python is rendering that text — which is not a
round-trip of anything — and the choir's foresight, a package answering a question, which could
as well be a belief the update reads.

# What was refused: the search as updates

A fork is copy-graph-and-apply-diff in the store already, and the effect is a rule
([planning-branches-on-action-forecasting-on-belief](/decisions/planning-branches-on-action-forecasting-on-belief.md)).
What is Python in the [imaginarium](/domain/imaginarium.md)'s pass is not the fork, it is the
CHOICE around it: which node to expand next, when the budget is spent, which worlds have been
seen by signature, which levers the closure keeps. An update is one fixpoint step — every row
at once, no order among them, no budget, no stop. Breadth-first would fit that shape, one update
per depth expanding every frontier world by every action; and breadth-first is the order under
which an admissible estimate refused nothing, because the first achiever came last, and
best-first is what a pass is budgeted under
([a-pass-is-budgeted-in-worlds](/decisions/a-pass-is-budgeted-in-worlds.md)). The measurement
closes it from the other side: a real pass forks for a tenth of a percent of its time and reads
for fifteen, so the round-trip is not where the cost is, and the reads are SPARQL already.

**Refused, not deferred.** The alternative was live — the same `INSERT { GRAPH ?child { … } }
WHERE { GRAPH ?parent { … } }` that would materialise a view can mint a child world per row —
and it is turned down because a search is a sequence of choices and an update has none in it.
The trigger for reopening is a search whose order is not a choice: a saturation rule (#569) is
one, and is a rule for exactly that reason.

# What was refused: repositories as rule executors

The repo already holds both shapes, and the question is which line runs between them. A
package's `rules.ru`, `desires.ru`, the effect and precondition texts in `actions.ttl` and a
`review.rq` are read-write rules run by an executor — genesis, the imaginarium, review. `Wants`,
`Desires` and `Affordances` are collections read by Python that decides. The line is:

**A rule for what is a function of the data. Python where a dataset is chosen or an order is.**

Turning a repository into an executor would not move that line, only rename the thing on
the Python side of it; and turning the deciding Python into rules is the search-as-updates
refused above. The repository stays what it was named for
([a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md)), and its `save`
is the update it always was.

# The cost a rule carries, and how a derivation written as rules pays it

The most repeated bug class in this project is a query that binds nothing and says nothing —
half the traps in AGENTS.md are one. An `INSERT … WHERE` that mints no want is silent in exactly
that way, where the Python logs the page it read and says which desire reads unmet and
what it is pursuing. A derivation written as rules therefore runs its `WHERE` as a SELECT first — logged, and what
the tests assert on — and inserts second. That is a round-trip of rows, not of objects, and it
is the price of hearing an empty result.

# What is left

- The trial, on the derivation alone, reshaped by
  [judge-desires-then-derive-wants](/decisions/judge-desires-then-derive-wants.md):
  `derive_wants` chooses the dataset per instant at the door, in Python, so it needs no view
  per instant; and `scope_actions` writes the scope partition to the store at boot, so it is
  data. What is left of the trial is the derivation itself as one update. A/B alternated
  within one session, as this bench requires.

# Seams left open

- **A view per instant is a copy of the world per prediction start.** An agent holding many
  predictions holds as many views; the bound is the count of starts, which sensing and the ledger
  keep small today and nothing caps.
- **The choir's foresight is Python**, a package answering a question at derivation time.
  Closed by deletion rather than by a rule: the foresight filtered judgments that already
  carry their instants, and how far ahead the agent sees is the horizons each drift predicts
  at ([judge-desires-then-derive-wants](/decisions/judge-desires-then-derive-wants.md)).
- **A scope over variables** (#565, #663) changes the partition and not the mechanism: a
  finer partition is more groups in the same `GROUP BY`.

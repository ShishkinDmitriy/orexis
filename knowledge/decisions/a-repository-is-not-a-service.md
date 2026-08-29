---
type: Decision
title: A repository is not a service, and Component was both
description: >-
  One word covered two kinds of thing, in the code and in the bundle's types. `Beliefs` and the
  imaginarium passively hold data scoped to one agent; the deliberator, the keeper and six others
  hold logic — and `Component`'s own definition named the two repositories as its examples, so it
  was explained by the passive half while being applied to the active one. The alternative was to
  keep one word and let authors judge, which is what had been happening; it is refused because
  nothing the word said helped anyone choose it.
status: accepted
timestamp: 2026-08-29T00:00:00Z
---

# Three layers, and the code already had them

| layer | what it is | examples |
|---|---|---|
| store | raw graph access — `query`, `update`, `put_graph`, `optimize` | `agent/store.py::Store` |
| repository | wraps a store, scopes it to THIS agent, exposes `read()` | `Beliefs`, `Desires`, `Intentions`, `Imaginarium` |
| service | holds the logic | the planner, the deliberator, the keeper, `owing`, `revision`, `inference` |

**A repository is built two ways here and both are fine.** `Beliefs`, `Desires` and `Intentions`
WRAP a store and delegate; `Imaginarium` and `_Derivation` EXTEND one. The
[imaginarium](/domain/imaginarium.md) is a full repository — its domain method is `reached()`,
which mints the graph for a search node — and it belongs to the planner rather than the agent,
which is why an audit of the constructor missed it.

**A repository also carries its own support functions.** Compaction was written as a service and
is not one: it decides nothing, asserts nothing, and reclaims bytes belonging to one repository,
so it is a function of [belief-base](/domain/belief-base.md). Writing no graph is only the hint —
three services write none either, and stay services because each decides something.

# The types follow, and Component folds

`Component` meant *a part of the implementation* and carried nine pages: two that hold data
([belief-base](/domain/belief-base.md), [imaginarium](/domain/imaginarium.md)) and seven that
hold logic.

**Its own definition gave it away.** It read *"a part of the implementation — the belief base,
the imaginarium"*, and both examples are in the first group: the word was explained by the
passive half while being applied to the active one.

**The alternative was to keep it**, either as the single word it had been or as a home for
whatever fit neither half. Refused, because a type falling to one member is a type to fold back
and this one falls to NONE once both halves are named — and keeping a word that means *neither
of the two things this is* is not keeping a kind of thing. The choir is the only member worth
arguing, and it is a service: the mechanism by which services ask each other is dispatch, not
data.

**Two repositories is thin, and it is the honest count.** The mind has four today and six in the
target, but only two can have pages: [desire](/domain/desire.md) and
[intention](/domain/intention.md) already state what their stores are, and a repository page for
either would be a second owner of a claim. Pointing beats extracting, so the count follows.

# The picture draws the target, not today

[`diagrams/agent-structure.puml`](/diagrams/agent-structure.puml) draws the six modalities with
one repository each and marks the delta from what runs. Drawing the current state would produce
a registry — a list nobody gates, which the next change makes wrong in silence. A target has a
reason to be re-read: it is either reached or amended.

# What this found, and left

- **`Desires.rebuild()` is a service inside a repository.** `_Derivation(Store)` runs every
  package's `desires.ru` from within the repository the runtime is supposed only to read. The
  intent holds; it is kept true by hiding the writer inside rather than by the layering.
- **Two graphs sit in a store that is not their modality.** `graph/actions` is menu-modality and
  `graph/deliberation` is possible-modality, both in the beliefs store — while the imaginarium,
  also possible-modality, is a store of its own. That is the one rule
  [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) exists to state, unmet in two
  places.

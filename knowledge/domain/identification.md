---
type: Domain Concept
title: Identification
description: >-
  Which child of the root the present is in, asked after an action and whenever the present
  changes. The match becomes the root, its siblings die, the old root goes to history. Not
  asserting a prediction — the present's content is observed, its position in the tree is the
  matched child. Named by the record the-future-is-a-cone; not built (#554).
---

# What it is

Execution walks the [imaginarium](/domain/imaginarium.md)'s tree. When a step has been taken,
and equally when a reading arrives or another agent acts, the question is not "did my prediction
hold" but "which of the worlds I imagined is this one". Each child of the root predicted an
[interval](/domain/interval.md) and has a next step with a [precondition](/domain/precondition.md);
the present is in the child whose interval it lies inside and whose next step still applies.
That child becomes the root, its siblings and their subtrees are dropped, and the old root is
the newest entry in [history](/domain/history.md).

The difference from asserting the prediction is the whole point. The present's **content** is
what the sensors say. The present's **position** in the tree is the matched child. When the
world landed in a sibling the search had explored — an action's other outcome — the plan
continues from there with no search. When no child matches, the tree is dead and a search starts
from the present.

# What it is not

- It is not the [keeper](/domain/keeper.md)'s verdict, which holds the committed step to its
  prediction and advances the ledger. Identification is what happens to the tree afterwards.
- It is not a tolerance of its own. The interval's width is the tolerance.

# Not built yet

The keeper holds one committed step to a band computed at execution and drops the whole plan
when it is unmet; nothing asks the siblings. The issue is
[#554](https://github.com/ShishkinDmitriy/orexis/issues/554).

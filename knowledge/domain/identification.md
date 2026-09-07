---
type: Domain Concept
title: Identification
description: >-
  Which kept world the present is in, asked at the start of a pass: within the want's view,
  the present's diff against the old base is looked up among the kept worlds; the match
  becomes the root and its siblings die. Not asserting a prediction — the present's content
  is observed, its position in the tree is the matched world. Exact within the view until
  intervals loosen it.
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

# How it runs

At the start of a pass, on the worker thread the search runs on (#554). The keeper's events —
a plan finished, a plan failed, a step done — and a reading landing all wake a pass through
the reviser, and the pass begins by asking whether the invariant half moved and, if not, which
kept world the present is; identification is not run on the reactive loop against a cone the
worker may be reading. The match is made WITHIN THE VIEW: the predicates the want's closure
names, and for a reading the property the want is about, so a fact the want never reads may
drift — the butt's level under a moisture plan, a stray fact in a courier's world — and the
cone stands. The match is exact within the view, a reading by its value, which is right where
nothing moves but the agent and is why a plant cone dies at the first reading that lands a
little off its prediction; [interval](/domain/interval.md) matching (#556) is what loosens it.

# What it is not

- It is not the [keeper](/domain/keeper.md)'s verdict, which holds the committed step to its
  prediction and advances the ledger. Identification is what happens to the tree afterwards.
- It is not a tolerance of its own. The interval's width is the tolerance.
- It is not yet the bridge's road: a kept promise still writes its predicted facts into the
  readings graph until the level above derives them by a saturation rule
  ([#569](https://github.com/ShishkinDmitriy/orexis/issues/569)).

# Not built yet

A reading of another property that a relevant lever reads — the butt's level, which
acquiring reads — is outside the view today, since relevance names predicates and every
reading carries the same ones; a plan resumed across such a drift is caught at execution by
the keeper's readiness, and would be caught at the re-root by the next step's
[premises](/domain/precondition.md) once they are asked there. Interval matching is #556.

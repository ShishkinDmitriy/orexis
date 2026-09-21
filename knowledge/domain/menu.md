---
type: Domain Concept
title: Menu
term: http://example.org/orexis#MenuGraph
description: >-
  One of the six modalities the mind is made of, and the alethic one - what the agent COULD do,
  beside belief's what IS and intention's what I am DOING. It is not a collection and has no
  class: what is STORED in it is the actions, and what it comes to for one agent in one world is
  the steps, which are derived on every ask and written nowhere. The word had been doing
  all three jobs, and a reader who met it could not tell which.
---

# What it is

A **modality**, not a store of some particular thing.
[the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) sets them out in one table, and
this is the row that asserts *what I could do*:

| graph | asserts |
|---|---|
| belief | what IS |
| constraint | what MAY be |
| desire | what I PURSUE |
| **menu** | **what I COULD do** |
| intention | what I am DOING |
| history | what I DID |

`orexis:MenuGraph` is the class, and `orexis:ActionGraph` sits under it: a modality with one
kind of thing written into it and one kind derived out.

# The two things inside it, and neither is called this

**Written in**: [actions](/domain/action.md). One node per way of acting, shipped by the package
that owns the action, carrying the precondition that says when it is possible and the effect that
says what taking it would make true. Stored, and safely — a schema outlives nothing. Their
collection in the code is `Actions`.

**Derived out**: [steps](/domain/step.md). What one action comes to for one agent in one world,
which is where its parameters and the want get bound. Never written, for the reason
[step](/domain/step.md) gives. Their collection is `Steps`, which is also what loops the
templates into a world.

So this modality holds rules about actions and never what fills them — which reads as a puzzle
until the modality and its contents are told apart.

# Why the word needed pinning down

It had been naming all three: the modality, the templates, and the rows. This page itself opened
*"the modality that holds what could be done"* and then described the templates, while typed as
though it were their collection; other pages used it for the rows. A reader meeting it had no way
to tell which was meant, which is how an action and a step came to feel like one thing
when they are a schema and its situated instance
([a-situated-instance-is-kept-only-when-it-is-testimony](/decisions/a-situated-instance-is-kept-only-when-it-is-testimony.md)).

The word keeps the sense that has a term behind it and a row in the table above. Records written
before this use it more loosely; where one says the menu is computed per ask it means the
steps, and where it says the menu is what the packages contribute it means the actions.

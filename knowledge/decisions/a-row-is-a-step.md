---
type: Decision
title: A row is a step, and the service between two collections was a loop
status: accepted
timestamp: 2026-09-21
description: >-
  An `Affordance` and a `Step` were one shape in two classes, with a `from_row` copying four
  fields from one into the other the moment anything wanted to plan. They are one class now, and
  the `Afforder` that stood between the two collections turned out to fetch nothing and decide
  nothing, so it is `Steps.find_all`. What this refuses is keeping a second word for the same
  thing at a different moment.
---

# What was wrong

Two frozen dataclasses. `Affordance` carried `action`, `binding`, `want`, `for_agent` and
`is_own`. `Step` carried those five plus what a search adds — the quantity, the window, the
prediction, the precondition, what it was expanded from. A strict subset, and the proof was
`Step.from_row`, whose whole body copied four fields across.

Six call sites converted. `deliberator.py` wrapped one in a plan with
`Plan(OBLIGATION, ((Step.from_row(row)),))`; the planner sized one with
`Step.from_row(row, quantity=…)`; three tests did it to hand a row to execution. Nothing was
added by the conversion that `None` in the absent fields had not already meant.

**Two classes for one shape is how a reader comes to believe there are two concepts.** The
dictionary had a page each, and both were right about their own half: a row is *derived and never
stored*, a step is *planned and written to the ledger*. Neither noticed that the second word was
doing no work the ABSENT FIELDS were not already doing.

The sovereign's line settles what the one word then means: **a step is an action picked for
execution.** Planning finds a plan, every action in a plan is a step, and what a step adds to
the action is at least the variables it was picked with. So a world ADMITS one of these per
action per legal filling, the search ranges over them, and the picked ones are the plan's
steps — one shape, and the picking is what the extra fields record.

# What we do instead

One class, `progression:Step`, and one page. `Steps.find_all_by_action` yields what a world
admits; a plan holds the picked ones; `from_row` is gone, and where a search re-sizes one it is
`dataclasses.replace`.

The argument each page owned survives on the one that is left: what a world admits is derived,
because a stored one can outlive the plumbing it was concluded from, and a PICKED one IS written,
because it is no longer a conclusion about the world — it is a commitment, and the ledger is
where a commitment belongs.

# The service went with it

`Afforder` sat between `Actions` and `Steps`, and its record said it held logic rather than a
query. Read again with the word gone, it fetched nothing and decided nothing:

- **the actions worth asking** were the caller's `only` — the search computes relevance and
  passes it;
- **what the agent holds** was handed in, by its own docstring: *"being told is not the same as
  fetching it"*;
- **the merge** was a loop and a sort.

A thing that decides nothing is a repository's support function rather than a service, which is
this repo's own line. So the loop is `Steps.find_all`, and the four identities the service held
— the templates, what the agent holds and what each want is about, and whose world this is — are
criteria of the ask, exactly as the inner `find_all_by_action` already took them. The collection
still holds a store and nothing else.

What is lost is a convenient place to keep the criteria. A search fills them once per pass
(`Planner._offered`), the container holds `actions`, `steps` and `picks`, and the two remaining
callers spell them. That is four extra arguments at three sites against a class, a file, a
dictionary page and a decision record.

# The alternative, and why it was refused

**Keep `affordance` as the word for one that is available but unpicked**, with no class behind
it. This is what a reader would expect: picked and unpicked are genuinely different, and English
has a word for each.

It was refused because it reintroduces exactly the thing the sovereign objected to — *"the same
concept used differently based on situation"*. A reader meeting both words looks for the
difference, finds it is a matter of when rather than what, and the definitions drift from there;
that is how `lever` and `means` became separate concepts, and how a disk came to be called a
lever. One shape, one word, and the moment is said by what else the step carries.

The **metric key was renamed with it** — `affordances_suspect` became `steps_suspect` — on the
sovereign's ruling, at the cost of the series history on the live terrace world. A key that
outlived its word would be the same drift in telemetry.

# Seams left open

- **`menu` still names three things**: the modality, the templates written into it and the steps
  derived out. [menu](/domain/menu.md) exists to disentangle them, which is a page doing a word's
  job.
- **`Steps.find_all` takes four criteria and a keyword.** It reads long at the three sites that
  spell them. Whether the container should hand them as one thing is open; handing the agent
  would make the collection know about an aggregate root it has no business knowing.
- **A step now carries fields that are meaningless until it is planned.** Nothing stops a caller
  reading `predicts` off a step a world merely affords; it is `None`, which is honest, but the
  type does not say so.

# Related

- [an-action-takes-parameters](/decisions/an-action-takes-parameters.md) — the change before
  this, which made the binding the row's identity and so made the two shapes identical.
- [step](/domain/step.md) — the one page now.
- [an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan](/decisions/an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan.md)
  — why a step is not an act, which is untouched.

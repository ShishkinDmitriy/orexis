---
type: Decision
title: An action takes parameters, and the kernel names none of them
status: accepted
timestamp: 2026-09-21
description: >-
  The kernel carried five named columns on every row and every step — a lever, what the row was
  about, which way it moved it, whom it served, which want — and interpreted none of the first
  three. An action declares what it `orexis:takes` instead, its precondition projects one
  variable per parameter, and the binding travels as opaque pairs the declaring package alone
  reads. What this refuses is the alternative that had already been taken once: adding a sixth
  named channel when a domain needs a second parameter.
---

# What was wrong

`Affordance` and `Step` each had a fixed shape, and three of its columns were the kernel's own
invention: `via` (a lever), `about` (what the row moved) and `direction` (which way). Every
package had to express itself in those three, whatever its actions were actually filled with.

The strain was visible in the code that shipped. `hanoi:Move` needs a disk and a destination
peg, so it said, in its own comment, *"`$via` says which disk, `$about` says which peg"* — a
disk is not an instrument and a peg is not a property. The courier's three actions did the
same with a van, a parcel and a cell. And the history is in the planner's own text: a two-
parameter action was **inexpressible** at first, so hanoi shipped six ground actions for one
move; `$via` was then added as a second channel, which bought one more parameter and not N.

It hid a defect, too. `market:Serving` binds its valve from `actuation:hasActuator`, while
`hosting.py` minted a Serving step with `via=market.uri` — a venue. Two writers put two
different kinds of thing in one column and nothing could tell, because nothing read it.

And one column was pure ceremony: `direction` was projected by four preconditions, copied from
row to step, and read by **no line of Python and no rule** — only by two tests, as the witness
that a precondition does not cross-join two venues.

# What we do instead

An action declares its parameters, in the declaring package's own words:

```turtle
hanoi:Move a orexis:Action ;
    orexis:takes hanoi:disk, hanoi:onto ;
    orexis:available """SELECT ?disk ?onto WHERE { … }""" ;
    sh:construct """CONSTRUCT { $disk hanoi:on ?dest } WHERE { … }""" .
```

A parameter's **local part is one spelling in three places** — the variable its precondition
projects, the `$token` its rules read, and the predicate a planned step is written under — so
nothing maps between them. A row carries `binding`, the sorted `(parameter, value)` pairs its
precondition bound, and that binding **is** the row's identity.

The kernel uses the pairs for exactly three things and reads no value:

- telling two rows of one action apart, which is what names the world a step reaches;
- stating what a step is, in the ledger and in the trace, one triple per pair;
- handing each value to that package's own rules as `$<local part>`.

`want` and `for_agent` stay the kernel's, because the search genuinely branches on them: which
want a step advances, and whether a row is the agent's to propose or an obligation to honour.
`direction` became `market:direction`, a parameter the market declares — so the guard keeps its
witness and the kernel loses the column. `orexis:about` stayed the word it already was and
became a parameter most actions declare, which is what a step was already written with.

# The alternative, and why it was refused

**Add a sixth named channel.** This is not hypothetical — it is what was done the last time,
and it worked: `$via` was added precisely so `hanoi:Move` could stop being six nodes. The same
move would have let `market:Serving` carry a venue *and* a valve.

It was refused because the cost is paid by every package and the benefit by one. A named column
is the kernel claiming to know what kinds of thing an act is filled with, for every package that
exists and every one that does not yet. Each addition widens two dataclasses, the ledger's
writer and reader, the trace, the world-naming function and the refusal key — and leaves the
NEXT domain in the same position, choosing which of its parameters to misname. Counting the
channels is the tell: five columns, two invented, one dead, and a disk called a lever.

The second alternative, **leave `direction` deleted**, was refused on reading: two tests assert
on it as the witness that a precondition does not cross-join, so it is not garbage — it is
domain data the kernel should not have a slot for, which is the whole thesis.

# What it cost

A method's member inherits the binding of the step it was expanded from, so it carries pairs
its own action never declared. Reading a step back held to its OWN declaration dropped them
silently: a `market:Tendering` expanded out of an `market:Acquiring` lost the property it was
about, and the bidder **declined its own step** for being about nothing. The read-back is
joined to what any action declares a parameter now — a step carries what it was filled with,
and the ledger gives it back whole.

The one-time migration for volumes older than
[an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan](/decisions/an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan.md)
still moves `progression:through` onto the act, and nothing interprets that predicate any more.
Such an intention stands with nothing bound until it lapses and is planned again.

# Seams left open

- **`affordance` and `step` are one shape and two classes.** `Step.from_row(row)` copies four
  fields across; the row IS the step, minus what the search adds. Folding them would delete a
  class, a conversion and a word.
- **`menu` is still a word for the set of rows**, with 96 sites in Python. It names a modality,
  a collection and its contents, which is what [menu](/domain/menu.md) exists to disentangle.
- **Nothing gates an action against its declaration.** A precondition projecting a variable the
  action does not declare is silently ignored, and a rule reading a `$token` nobody declares
  refuses only at simulation time. The audit that found `sensing:Observing` projecting an
  always-unbound `?direction` was run by hand.
- **`orexis:about` still declares `rdfs:domain orexis:Desire`** while being a parameter a step
  is written with. The closure is materialised at genesis and never runs over a step, so nothing
  observes the false entailment — but the declaration is wrong.

# Related

- [the-action-is-the-kind](/decisions/the-action-is-the-kind.md) — the record that folded
  `means` into `action`; this one folds the columns.
- [affordance](/domain/affordance.md) — the row, and what its binding is.
- [action](/domain/action.md) — the schema, and what an author writes.

---
type: Decision
title: A shape is named for what it checks, and the name is most of what a reader sees
description: >-
  A boot gate prints a message; a reader chasing it back arrives at a name. `BeyondSurvivalShape`
  was named for a hand-written survival check that had moved into the deduction, so its one
  surviving constraint — a region nothing watches — was reported under a heading about dying,
  and the page describing it reached for a term that existed nowhere. Renamed, and the sweep the
  issue asked for found two more. A comment that disagrees with its constraints is not
  mechanically checkable; a comment that is absent is, so that half became a gate.
status: accepted
timestamp: 2026-08-28T12:00:00Z
---

# What was wrong

`sensing:BeyondSurvivalShape` (`ag:BeyondSurvivalShape` before the stake moved) was named and
commented for one check: *the last reading of a property this agent has a desire in lies outside
what its subject survives*. That check is gone, and rightly — the deduction emits it now, as a
shape targeting the subject, saying the same sentence in the language the checker already speaks,
and `|gap| = 1` in `gap.rq` is the same fact as a number. Two statements of one rule is one too
many.

What was left behind is the name. The **only** constraint under it was unrelated:

> a desire in a property this agent polls no sensor for — the region is real, and the agent will
> never see a reading to hold it to

So a warning about a blind region arrived under a heading about dying. It is live: it accounts for
every warning line `orexis-validate loner` prints.

**The tell was in the bundle.** `domain/desire.md` cited this constraint as
`desire:UnwatchedDesireShape` — a term that exists nowhere in the repo. Whoever wrote the page
reached for the name the constraint deserves and did not check that the code had it, which is the
clearest evidence available that the name described nothing the shape does. (The term guard added
for [#275](https://github.com/ShishkinDmitriy/orexis/issues/275) is what surfaced it.)

# What is decided

**`sensing:UnwatchedRegionShape`**, with a comment describing the constraint that is actually
there. It uses [region](/domain/region.md)'s word rather than *desire*, because a region is what
the agent holds and what goes unwatched.

**And the sweep the issue asked for was done** — every named shape in the repo, its name and
comment against the paths and messages it constrains. Two more of the same species:

- **`market:MarketShape` said *all three of its channels* and demanded four.** Offer, bid, claim,
  redeem — the redeem channel arrived with the presentation and the count did not follow. A
  comment describing a shape one constraint smaller than the one underneath it.
- **`ag:WorldVersionShape` had no comment at all**, alone among every shape in the repo. A version
  is one whole number, and it is what an observation stamps itself with, so a world whose version
  is missing or doubled makes every reading taken under it unattributable. Now said.

Everything else matched.

# What can be a gate, and what cannot

**A comment that DISAGREES with its constraints is not mechanically checkable.** SHACL does not
care what a shape is called, and no gate can read a sentence and a set of paths and say they
contradict each other. Both findings above needed a reader.

**A comment that is ABSENT is checkable**, and that is now
`tests/test_shapes.py::test_every_shape_says_what_it_is_for`: every named `sh:NodeShape` carries a
non-empty `rdfs:comment`. It is the weaker half and worth having anyway — a shape with no sentence
cannot be compared to its constraints by anyone, so the drift that produced #275 could not even be
looked for. Blank-node shapes are excluded: an `sh:property [ … ]` is a constraint rather than
something somebody names, and it carries an `sh:message` where it needs to speak.

This is [one-word-for-one-relation](/decisions/one-word-for-one-relation.md) applied to shapes
instead of properties, with one thing added by the medium: a property's name is read by whoever
writes a query, and a **shape's name is read by whoever is already in trouble**. The gate prints
the message; the name is where they land next.

# Seams left open

- **Nothing checks that a shape's name matches its constraints**, and nothing can. What this
  change leaves is a sweep somebody did once, and a record saying what it found — so the next
  reader knows the question has been asked and what the answer was.
- **A comment can be present and wrong.** The gate below only proves a sentence exists.
  `market:MarketShape`'s said three for as long as there had been four, and passed every gate
  there has ever been.

---
type: Decision
title: Deliberation is on triples, and a number is not special
status: accepted
timestamp: 2026-09-07T18:00:00Z
description: >-
  The core deliberates on triples and interprets no literal. How a domain describes its world —
  exact numbers, ranges, classes — is decided inside the domain, and its actions' preconditions
  and effects are described the same way, so a range, a cell and an interval are not concepts of
  the core. The plant domain chooses classes over its ranges, minted per want by the derivation
  that mints the want, and a reading is classified by entailment; progression computes the
  numbers at execution, sizing the dose or the lot to reach what the step promised. Refused,
  each after being built: a partition the kernel reads off the shapes and selects (#573), a
  predicted number carried in the core as an interval (PR #575), and the search sizing an act
  during simulation. The cost, taken knowingly: two acts each too small to cross a boundary are
  found by re-planning after the first lands, not by search.
---

# The ruling

The sovereign, 2026-09-07, reading the interval PR: *a range or a cell is not a concept of the
core; it is domain-specific, and for OWL we have rules that expand — derivations.* And then: *the
same handling: a range becomes a class, so the core just sees the precondition as this class and
the postcondition as another class — just triples, no need to know specific numbers. Progression
calculates the final values at its stage; when it starts Bidding it calculates how much and bids.
Not core.* And on reading the first draft of this record, which said "classes": *it is not
strictly classes. It is decided inside the domain. It could be strict numbers, but then actions
are described as numbers; or it could be ranges, and preconditions are also described in ranges.
We are just deliberating on triples. We do not handle numbers differently.*

# The claim

**The core deliberates on triples and interprets no literal.** A [step](/domain/step.md)'s
[precondition](/domain/precondition.md) and its [effect](/domain/effect.md) are triples in
whatever vocabulary the domain describes its world in; the signature states a world as the
triples it holds; identification, cycle detection, met and the regression are triple equality;
the keeper's verdict is whether the promised triples are there. Nothing in the core knows a
number from a name. A domain that describes its world in exact numbers describes its actions in
exact numbers, and the world must answer with the number the step said. A domain that describes
its world in ranges describes its preconditions in ranges. Hanoi and the courier describe theirs
in plain facts and always did. No cell, no interval, no partition, nothing keyed by a number in
the core — and no rounding: the one numeric special case the signature still carries, six
places on every literal, goes with the build, and a rule writes the number it means.

**The plant domain chooses classes over its ranges.** `orexis-plant-water` declares what a
reading of its properties can be — dry, in region, wet, and the butt's empty, low, full — as OWL
classes with datatype restrictions on the value they classify. Dry is relative to the plant, and
a restriction takes a fixed literal, so the MEMBER classes are minted per want by the derivation
that mints the region want from the range the world states (`desires.ru`, on the desire
modality's rebuild, so a class keyed to a pick moves when the pick does). The shape says what
must hold and the class says what a reading is, both from one range, so there is one owner. The
domain already had the word: `water:Band` with `LOW` and `OK`, the alarm band a board keeps,
stated as instances. A reading is classified by entailment, the way the closure already turns
`owl:hasValue` into ground triples (`agent/inference.py`, rule 5): a datatype restriction over a
number is the second OWL construct a materialising closure can honour, computed for a reading
and never asserted, since the interpreter already knows the number. This is the plant domain's
decision, and another domain may decide otherwise without the core noticing.

**Progression computes the numbers.** The effect rule stays SPARQL in the package and describes
what a dose reaches in the domain's vocabulary; the actuator sizes the dose and the bidder the
lot at execution, from the reading in hand, to reach what the step promised — what `dose_for`
and `qty_for` do today. The search stops asking the taker to size during simulation. Cost and
the estimate stay numbers, since they are measures the package owns rather than beliefs the core
plans on; how urgent a state is, is the measure's to say.

# What was refused, each after being built

- **A partition the kernel reads off the readers** (#573, merged as PR #574). `partition.py`
  reverse-engineered thresholds from the constants in shapes and selects, and a cell was a Python
  tuple nobody could state in the graph: a premise rendered as FILTERs, a remembered plan's
  precondition nobody could query, the kernel guessing the domain's states from the numbers its
  readers happened to compare against. Right about the identity — two readings no rule tells
  apart are one fact — and wrong about the owner.
- **A predicted number carried in the core as an interval** (PR #575, closed unmerged). The
  effect declared two ends, the signature folded them into one fact, the keeper held the world to
  the pair, and identification asked whether the present lay inside. Four vocabulary terms to say
  "interval", and every one a numeric concept the core then reasoned on. The argument for it — the
  search finds dose, look, dose when no single dose is certainly enough — survives as a seam below,
  in the domain's terms: an effect with two possible outcome classes.
- **The search sizing the act.** `orexis:size` was asked per fork so the effect could predict a
  number, which put a package's arithmetic on the search's path and a number in every world. The
  act is sized once, when it is taken.

What the interval record refused stays refused: no tolerance applied at verification by an
actor, no kernel-wide width, no tolerance owner apart from the effect. They are refused by
absence now — the core carries no width at all.

# What it costs

Two doses each too small to cross a boundary, together crossing it, are no longer a plan the
search finds: dry to dry is a no-op world, and the cone prunes it. Progression pours what stock
allows, the world answers "still dry", and the next pass plans the next dose. That is "the world
verifies it, not a search" applied to the plan's length, and it flips
`test_a_second_dose_is_predicted_from_what_the_first_one_left`. Urgency ordered by class is
coarser than urgency by distance, which is the ruling's point: a pot at 25 and a pot at 27 are
one world.

# Seams left open

- **Where the plant domain's membership is computed** — at the signature, reading the T-Box's
  restrictions, or materialised into a possible world at the fork. Measured in #576. Either way
  it is the domain's derivation the core runs, not a number the core reads.
- **An effect with two possible outcome classes**, and the look that tells them apart — the
  dose-look-dose plan the interval record wanted, restated as a disjunctive effect. Not built.
- **The interval as the package's own tool** for sizing under a learned tolerance, inside
  progression and never on the core's road. The tolerance term and its residual review stay,
  reading the numbers progression records at execution.
- **The law's ceiling and a pick's aim as classes** — each a reader's claim stated once, and each
  held to the test that something plans on it.
- **The name** — the precondition page is bound to `progression:premises`; #580.

# The build

The plant domain's choice, built:

[#576](https://github.com/ShishkinDmitriy/orexis/issues/576) mints the classes and classifies a
reading, and retires the kernel partition; [#579](https://github.com/ShishkinDmitriy/orexis/issues/579)
makes the effect declare its class and moves sizing to execution. #556, #557 and #558 are closed
as superseded; PR #575's branch stays as the numeric road refused.

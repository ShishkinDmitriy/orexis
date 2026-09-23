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
classes with datatype restrictions on the value they classify — the [bands](/domain/band.md),
which the domain already had as a word. Dry is relative to the plant, and a restriction takes a
fixed literal, so the MEMBER classes are minted per (subject, property) that states a range, at
GENESIS by sensing's `rules.ru` from the same narrowing of ranges `desires.ru` computes for
the want — at genesis and public rather than in the desire modality's rebuild, because the
sensed writer classifies a reading in the belief base, where the modality's graphs are not; a
band keyed to a pick, when one is wanted, would be the rebuild's. The shape says what must hold
and the class says what a reading is, both from one range, so there is one owner. A reading is
classified by ENTAILMENT (`Store.entail`, #576), the way the closure already turns
`owl:hasValue` into ground triples (`agent_old/inference.py`, rule 5): a datatype restriction over a
number is the second OWL construct materialised here, asserted on the reading's node when it is
written, when a possible world forks, and when a volume boots, and gone with the node. This is
the plant domain's decision, and another domain may decide otherwise without the core noticing.

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

- **A band keyed to a pick** — the aim, revisable — would have to be minted on the desire
  modality's rebuild rather than at genesis, and classified from there; not wanted yet.
- **An effect with two possible outcome classes**, and the look that tells them apart — the
  dose-look-dose plan the interval record wanted, restated as a disjunctive effect. Not built.
- **The interval as the package's own tool** for sizing under a learned tolerance, inside
  progression and never on the core's path. The tolerance term and its residual review stay,
  reading the numbers progression records at execution.
- **The law's ceiling and a pick's aim as classes** — each a reader's claim stated once, and each
  held to the test that something plans on it.
- **The name** — the precondition page is bound to `progression:premises`; #580.

# The build

The plant domain's choice, built in two parts:
[#576](https://github.com/ShishkinDmitriy/orexis/issues/576) minted the classes and classified a
reading, retiring the kernel partition; [#579](https://github.com/ShishkinDmitriy/orexis/issues/579)
made the effect declare its band and moved sizing to execution. #556, #557 and #558 are closed as
superseded; PR #575's branch stays as the numeric path refused.

# What building it taught

- **The number goes out of the core in one move or not at all.** While an effect predicted a
  number and the search matched by band, both were true of a world and the two disagreed: a want
  inside its region was met by band and urgent by number, and the measure answered whichever the
  caller had asked with. What settled it is that a WORLD is judged by band and a ROW — a want the
  agent holds, with the reading in hand — is measured with the number, so the aim still ranks
  what an agent wants and no longer steers what the search plans.
- **The domain's declaration is read as data and evaluated by the kernel.** Membership as one
  SPARQL question cost 300 ms a call however narrowed, and a pass forks tens of worlds; read
  once per store and evaluated against a node's triples, a fork's question is a dictionary
  lookup. That is the compiler's bargain one layer over: the domain owns the declaration, the
  kernel owns how it is answered.
- **A guard written as arithmetic has to be rewritten as a fact.** Two of them: a bid sized to
  nothing changed no world, and its retraction was gated on the size — with no size, the gate
  held and the old reading survived beside the new one. And a lever that fabricates a reading
  where none stands looks like progress, since knowing where the pot is scores better than not:
  the rules require a standing reading now, and a look comes first.

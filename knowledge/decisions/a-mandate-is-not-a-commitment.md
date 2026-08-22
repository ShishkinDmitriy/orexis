---
type: Decision
title: A mandate is not a commitment, and the class is renamed to say so
status: accepted
timestamp: 2026-08-22T00:00:00Z
description: >-
  review:Commitment is renamed review:Mandate. The word commitment already meant two other
  things here, both anchored — REA's promised economic flow, which settlement-speaks-rea
  assigned to the claim, and BDI's commitment, which is an intention — while the review class
  was the one everyone, including its own rdfs:comments, called the mandate. Checked against
  vf:Commitment (fails every clause of the definition) and ODRL Permission plus Constraint
  (fits loosely, but nothing here consumes ODRL semantics, and an alignment nothing checks is
  a synonym). The internal word wins with the external checks recorded, which is
  settlement-speaks-rea's own method. review:commits keeps its name; no volume migrates,
  because the type is entailed from the range and never written.
---

# Context

One word, three concepts — and two of the three had external anchors:

- **REA / ValueFlows**: `vf:Commitment` is *"a planned economic flow that has been scheduled
  or promised by one agent to another agent"*.
  [settlement-speaks-rea](settlement-speaks-rea.md) assigned that word to the **claim**, whose
  record is literally titled "a claim is a commitment".
- **BDI**: an intention *is* a commitment — "a commitment to reduce a named gap by a named
  means", per [an-intention-is-an-amortised-deliberation](an-intention-is-an-amortised-deliberation.md).
- **`review:Commitment`**: how far one agent may re-pick one term — granted latitude, a
  governance fact. Twenty-five bundle files, AGENTS.md, review's Python comments and the
  class's own `rdfs:comment`s all call this thing **the mandate**; only the class name
  disagreed.

[every-term-in-its-own-house](every-term-in-its-own-house.md) already recorded the first
collision — *"a name collision, not an alignment. Ours is a governance mandate… Same word,
different concept"* — and stopped at recording it. The ubiquitous-language audit found the
recorded collision still standing, plus the BDI one beside it.

# The external checks, and why the internal word wins

Was the mandate itself an REA borrowing gone stale? Checked: `vf:Commitment` fails on every
clause — a mandate is not a flow, is not scheduled, and is not promised by one agent to
another; it is room granted by the sovereign over one setting. Keeping the name would not
align us with REA, it would use REA's word for a non-REA thing while the thing REA means by it
sits one namespace over, already mapped.

Was there a better external home? **ODRL** is the nearest: a mandate resembles an
`odrl:Permission` bounded by an `odrl:Constraint`. Not adopted, and the refusal is
[one-word-for-one-relation](one-word-for-one-relation.md)'s: nothing here consumes ODRL
semantics, so the axiom would be a synonym nothing checks. And the resemblance is loose —
ODRL permits *actions on assets*; a mandate grants a *range to a value*, and its presence is
itself the capability grant, which ODRL has no word for.

So the method is [settlement-speaks-rea](settlement-speaks-rea.md)'s: check the words against
the standards, state the deviations, and keep our own where the standard does not fit.

# Decision

`review:Commitment` → **`review:Mandate`**, with `commits` and `limitedTo` re-ranged,
`onTerm` re-domained, and `CommitmentShape` now `MandateShape`. `review:commits` keeps its
name: "the world commits this agent to a range" reads correctly and collides with nothing.

**No volume migrates and no world changes.** Worlds write mandates as blank nodes under
`review:commits` and never type them — the type is entailed from the property's range at
genesis, and entailed graphs are rebuilt, not migrated
([a-volume-can-be-older-than-the-vocabulary](a-volume-can-be-older-than-the-vocabulary.md)
covers beliefs, which never held this term).

After this, *commitment* means exactly two things, both external and both deliberate: REA's
(the claim, in settlement contexts) and BDI's (an intention). The governance thing is a
mandate everywhere, including in the graph.

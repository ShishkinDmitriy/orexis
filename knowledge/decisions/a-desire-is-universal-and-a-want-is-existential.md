---
type: Decision
title: A desire is universal and a want is existential, and the graph's period is the interval
description: >-
  The two kinds are disjoint because they are different QUANTIFIERS over the same interval - a
  desire must hold at every instant of its period, a want at some instant of it, which is
  maintenance against achievement. The interval is the graph's period, already written and
  already read at an instant by the door, so `orexis:bindsWhen` states a third time what the
  type and the period say between them - and a debt already states its window twice. Five of
  PDDL3's nine constraint forms fall out; the four that relate two conditions or count
  occurrences do not, and saying so is part of the claim.
status: accepted
timestamp: 2026-09-18T09:00:00Z
---

# The claim

[a-kind-is-a-type-not-a-binding](/decisions/a-kind-is-a-type-not-a-binding.md) made
`orexis:Desire` and `orexis:Want` disjoint and said *the type is the kind*. That is true and
thin — it says the classes differ without saying what the difference MEANS, which is why the
record could only argue from the bug it was fixing.

The difference is a quantifier. **A desire must hold at EVERY instant of its period; a want at
SOME instant of it.** Maintenance against achievement, ∀ against ∃, over one interval. Keep the
soil in its region throughout; get the disks home once; pour the litre once, before the window
shuts. That is why the classes cannot overlap: a node is not both universally and existentially
quantified over the same interval, and a subclass relation between them was never coherent.

**And the interval is the graph's period.** A want IS its graph since #645, every graph carries
an optional `dcterms:temporal`, and the door already reads it AT AN INSTANT — `public_graphs(at)`
and `recorded_graphs(at)` both filter through `_holding_at`, so a constraint scoped to a future
window is visible to a search standing in that window and hidden from one standing now, which is
[#620's design](/decisions/a-root-holds-always-and-an-outdated-graph-is-dropped.md) working unchanged.

# Which makes the binding a third statement of what two things already say

| holder | type | binding today | its graph's period | what the two say |
|---|---|---|---|---|
| region, freshness | Desire | — | none | holds always |
| greenhouse's bed | Desire | — | none | holds always |
| hanoi, courier, tower | Want | AtEnd | none | achieve once, no deadline |
| pursued, no crossing | Want | AtEnd | start only | achieve once, from now |
| pursued, from a crossing | Want | At | start and end | achieve within, at an instant |
| a debt with a window | Want | Within | start and end | achieve within |
| a debt with none | Want | Within | start only | achieve once, from now |
| a promise | Want | AtEnd | **none at all** | achieve once, no deadline |

Rows four and seven are the tell: a pursued want bound `AtEnd` and a debt bound `Within` carry
DIFFERENT bindings and IDENTICAL periods, and mean the same thing. The binding was drawing a
distinction that is not there.

**A debt already states its window twice** — `orexis:expiresAt` on the row, which becomes the
deadline the planner holds a candidate to, and `orexis:end` on its graph's period, from the same
claim expiry. One fact, two places, nothing keeping them in step. That is
[the row whose presence is meant to BE a fact](/decisions/a-root-holds-always-and-an-outdated-graph-is-dropped.md)
arriving from the other side.

**And the binding has almost no readers left.** After #680 there are two, and both filter
`IN (orexis:AtEnd, orexis:At)` meaning *not a debt* — a provenance test wearing temporal clothes,
which is the same defect one layer down. What they mean is the pursuit road's own family, and
that is classified on the graph already.

# One thing the period cannot carry

`orexis:At` and `orexis:Within` both have a start and an end. They are genuinely different — hold
AT a point against hold SOMEWHERE in the interval — and what separates them is
`orexis:holdsAt`, which the At want already carries. So the model is **type, period, and an
optional instant**, not type and period alone. Saying it as two would be the same over-tidying
this record is about.

# Five of PDDL3's nine, and the other four are a different shape

| expressible as a quantifier over an interval | not expressible |
|---|---|
| `always` — Desire, no period | `at-most-once` — counts occurrences |
| `sometime` — Want, no period | `sometime-after φ ψ` — relates two conditions |
| `within t` — Want, period ending t | `sometime-before φ ψ` — likewise |
| `hold-during t1 t2` — Desire, period | `always-within t` — nested quantifiers |
| `hold-after t` — Desire, start and no end | |

The four missing forms say something about TWO conditions, or about how often — no interval on a
graph expresses that, and a later attempt to force one in should read this row rather than assume
the model reaches further than it does. **"We can express all of PDDL3" is not the claim**; five
of nine with one mechanism is, and the other four would need a vocabulary relating two nodes.

Two of the five are new. Nothing today writes a Desire with a period — `hold-during` and
`hold-after` are expressible the moment the model is taken and are written by nobody.

# What this refuses

**Keeping `orexis:bindsWhen` as an authored statement of intent.** The argument for it is real and
worth writing down: an explicit term is checkable, and an author saying *this binds within* states
intent, where a period on a graph was written for a different purpose — how long the graph is worth
believing. Two answers.

First, that purpose is not different. The door is instant-parametric and #620 already treats *what
holds at an instant* as the question a search asks; a graph's period has been the interval a
constraint applies over since a round became a graph. Second, where the two coexist today they are
the SAME fact written twice, and the writer has to keep them agreeing with nothing to help — which
is how a binding and a period came to disagree about rows four and seven above without anything
noticing.

**And it refuses deriving the kind from the period.** The period says over WHAT interval; only the
type says with which quantifier, and a Desire and a Want with the same period are different
constraints. Reading the kind off the shape of the period would rebuild the exact confusion #680
took out — which is why this is not "the binding moves to the period" but "the binding was saying
what the type and the period already said".

# What is left, and where

The argument is here; what to do about it is tracked. **#681 is done** — `orexis:bindsWhen`,
`orexis:Binding` and the three remaining bindings are gone from the vocabulary, with
`orexis:BindingWantShape`. #682 folds `orexis:expiresAt` into the period a debt already carries,
#683 gives a promise a graph of its own, and #684 mints one per world-ratified want so a world
can state a window at all. Only the last is work; the rest is subtraction.

What the removal turned up is worth keeping: the four things the binding was saying each had an
owner already, and the two live readers wanted a FOURTH thing it was not saying at all. They
filtered on `orexis:AtEnd, orexis:At` to mean *not a debt* — whose road a want came by, which is
the graph's classification. `Wants.find_first_by_desire` scopes to `deliberation:PursuedGraph`
now, and `_CHILDREN_Q`'s filter turned out to be redundant twice over: the ledger writes no
`orexis:holds`, so a debt never matched it, and a promise carries no `prov:wasDerivedFrom`.

# Seams left open

- **Nothing gates the quantifier.** A Desire and a Want are judged by the same met-test machinery
  today; the ∀/∃ difference lives in the planner's treatment rather than in anything that checks
  it. Whether a maintenance constraint should be judged at every state of a candidate plan — which
  is what `always` meant and what no reader ever implemented — is the first thing to measure when
  a Desire with a period is first written.
- **A world cannot state a window on a want it ratifies.** Every authored desire and want shares
  `graph/desire/asserted`, so per-want periods need per-want graphs, minted at genesis. That is the
  only part of taking this model that is work rather than subtraction.
- **The promise is still the odd writer.** It gives its want no graph of its own and no period at
  all, which reads correctly under this model — achieve once, no deadline — but leaves it the one
  want the #645 sweep cannot drop.

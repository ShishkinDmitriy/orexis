---
type: Decision
title: A want met by absence, and the law beside it
description: >-
  #468 built, in the two halves the #467 sitting ruled. SOFT: an aversion is a capability
  package granted by the statement itself — `aversion:avoids`, one ratified node carrying
  the pattern whose rows mean ENTERED — deriving a want with no `orexis:metWhen`, because
  its met-test IS its measure reading zero: one text, one engine, against whichever world
  is judged, which closes before it opens the flat-versus-named-graph split a met-shape
  would have forced. Binary urgency, the achiever road out, cost picking among exits.
  HARD: a ratified `sh:Violation` shape over a runtime state is pruned at EXPANSION with
  never-newly-enter semantics — an agent already inside keeps its exit plans — and the
  next legal candidate wins by construction, which retires the no-fallback seam rather
  than implementing it. Measured on the bench: 53 ms per node, ≈372 ms a pass, paid only
  where a world ratifies law. Refused: a metWhen for the want, pySHACL for the pattern,
  a graph-distance gradient, and aggregation-now.
status: accepted
timestamp: 2026-09-01T06:18:51Z
---

# A want met by absence, and the law beside it

[#468](https://github.com/ShishkinDmitriy/orexis/issues/468), built as the sitting ruled it:
the SHALL NOT is soft — a want — and the MUST NOT is law — a shape — and neither borrows the
other's machinery.

## The soft half: one statement, three jobs

`aversion:avoids` is the premise, the grant and the want's content in one ratified statement,
the latitude cut ([self-review-is-a-capability](/decisions/self-review-is-a-capability.md))
applied again: being told what to steer clear of is the whole of what makes steering
meaningful. Its object is a NAMED node — a want minted from it must survive a rebuild, and a
blank node's label does not — carrying one `sh:select`, the pattern whose rows mean ENTERED.
The package (`packages/orexis-capability-aversion/`) derives the want, copies the statement
into the derived graph (the desires store drops its public premises, and a pattern left
behind would be a dangling reference), and answers the choir for its own kind.

**The want carries no `orexis:metWhen`, and that is the record's sharpest choice.** A met-shape
would have been a SECOND text beside the measure, and the two would have run on two engines
with two graph visibilities — pySHACL over the flat world, the measure over named graphs —
which is the exact split this repo has closed once already. Instead the met-test IS the
measure reading zero, the road a call already takes (#359): the ratified select, `$this` and
`$state` substituted (in the pattern, never the projection — a substituted IRI in a SELECT
clause is a parse error, found the first time it ran), one engine, whichever world is judged.
What this buys concretely: a held aversion scores 0.0 at the planner's root and the pass ends
SATISFIED with no steps — where the flat not-knowing fallback would have sent the search
shopping for a want that wants nothing — and an entered one is planned through the ordinary
achiever road, a candidate world where the pattern no longer binds being MET by the same
reading, with cost picking among the exits.

Urgency is binary, which the four-measures table calls sufficiency rather than a stopgap:
between entered and held there is nothing to be nearer to, and the frontier carries a
multi-step exit without a slope. A pattern that fails to RUN reads as entered — the loud
direction: a select the gates admitted and the engine refuses is a defect someone must see,
and a want stuck hot is how this architecture says so.

## The hard half: the law prunes at expansion, never-newly-enter

A ratified `sh:Violation` shape over a runtime state is not a want and gets no urgency: it is
LAW, and the planner now holds EVERY candidate state to it — the sovereign's every-step
ruling, built. At `_begin` the pass collects the violation-severity shapes the DATA carries
(world-authored; met-tests excluded by the linkage; empty in every shipped world, and then
the check never runs) and the base world's own violation keys. A candidate whose keys grow
is discarded before the met-test can crown it and never expands — so a plan that dips
through a forbidden state dies at the dip however well it ends, and the next legal candidate
wins by construction, which RETIRES the no-fallback seam ("ask the next candidate") rather
than implementing it.

**Never-NEWLY-enter is the clause that makes the gate safe**: the subtraction against the
base's own keys means an agent already standing in a forbidden state keeps its exit plans —
the same argument that made the envelope a warning at the gates, honoured from the planner's
side, and pinned by a test that starts inside and demands the exit.

Measured on the bench before shipping, per the issue's own condition: 53 ms per candidate
node against an 8-triple law, ≈372 ms across a 7-node pass — paid only where a world
ratifies law, and the full rulebook stays at the gates.

## What was refused

- **A metWhen on the want** — the two-texts, two-engines split above.
- **pySHACL for the pattern** — same refusal from the other side; the measure's engine is
  the store's, everywhere.
- **A gradient over the pattern** — the graph-distance refusal
  ([urgency](/domain/urgency.md)) applied at its first temptation: where partial progress in
  a pattern must rank, decompose it into leaves.
- **Aggregation now** — avoidances penalising OTHER wants' candidate worlds is the
  ranking widened from the pursued want to the whole world, a real design with a real cost
  model, and folding it in here would have shipped it undecided. It is the seam below.

# Seams left open

- **The ranking still scores the pursued want alone.** An aversion is steered out of when
  pursued; a plan for a DIFFERENT want that wanders into an avoided (soft) state pays
  nothing for it yet. The law half covers the states that must never be entered; the
  aggregation that would price the merely-avoided ones is its own decision, with the
  composite-distance seam of [urgency](/domain/urgency.md) standing beside it.
- **The scope gate does not reach metWhen-less wants.** `orexis:ScopedWantShape` targets
  metWhen carriers; the aversion states `orexis:bindsWhen orexis:Always` by derivation, but
  nothing refuses one that stopped. The gate's target widens the day a second metWhen-less
  kind exists to generalise over.
- **The law is world-authored only.** A package cannot ship a violation shape over runtime
  states without it running for every world; whether a package should ever ratify law is a
  question no customer has asked.

# Issues this closes

[#468](https://github.com/ShishkinDmitriy/orexis/issues/468), both halves, with the
never-newly-enter clause and the measured per-node price its definition of done demanded.

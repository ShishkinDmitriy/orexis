---
type: Capability
title: Review
term: [http://example.org/orexis/review#ReviewCapability, http://example.org/orexis/review#Mandate]
description: >-
  An agent re-picking its own settings inside the room its world left it. Granted by LATITUDE —
  an `review:commits` mandate whose ends differ — so an agent given no room has no review module,
  keeps no summaries and never arises; the mandate is not a precondition checked at runtime, it
  is the premise the capability is derived from. A revision is legitimate exactly when
  `validate_agent` still passes, which is the same call the agent makes at boot, so nothing new
  had to be invented to judge one. Which terms may move is one triple in the owning package's
  ontology; the rule that moves them is SPARQL and never Python.
---

# What it is

A belief here is **a point chosen inside a range**, not a constant. What genesis wrote is the
first pick rather than a bound — so an agent whose world gives it room re-picks on its own clock,
and the author's job is to constrain well rather than to guess well.

**Review is the ability to do that re-picking.** A family with two members: `review:Reckoning`,
which decides by strict rules over its own recorded evidence, and `review:Consulting`, which would
ask a model. One is built and the other is deliberately empty, which is the family shape working
— the slot exists, and adding the second member changes no caller.

# Latitude is the premise, and the mandate IS the grant

There is no rule saying capabilities are granted by mandates. This one is, and the argument is
specific to it: **revising your own settings means nothing without settings you are permitted to
move.**

So `review:commits` — the mandate, in `world.ttl` — is what the derivation reads. An agent given
no room has no review module, keeps no summaries, and never arises. **A mandate whose ends meet is
no mandate**: `notBelow` equal to `notAbove` is a constant wearing a range, and it grants nothing.

That required the mandate to stop being a private belief and become public, which is the part
worth noticing: a capability derived from a fact cannot be derived from a fact only the agent can
see.

# What makes a revision legitimate

**Exactly what makes a boot legitimate.** A revision is allowed when `validate_agent` still passes
— the same call the agent already makes at startup — so nothing was invented to judge one, and a
revision that would make the agent unable to start is refused by the machinery that would have
refused the start.

Which terms may move is **one triple in the owning package's ontology** (`review:revisableToward`),
not a list here. A review rule is `packages/orexis-capability-<name>/review.rq` — SPARQL, never Python —
so a package that wants its settings revisable ships a query and nothing else.

# It reads evidence it kept, and writes only its own beliefs

Review runs on its own interval over **summaries** it accumulated: count, min, max, sum, sum of
squares, first and last instant, per (subject, property). Summaries rather than raw history,
because the belief base is not an archive and the statistics a re-pick needs are all recoverable
from those seven numbers.

Its write boundary is the agent's own beliefs graph and nothing else. It reads the world as
constraint and the sensed graph as evidence, and changes neither — which is what makes the graph
classes load-bearing rather than documentation.

# Compaction is not part of this

Reclaiming space in the belief base is **not a choice**, so it stayed in the kernel on a clock of
its own. The distinction is worth keeping: review is an agent exercising judgement inside room it
was given, and upkeep is housekeeping nobody deliberates about. Putting them together would have
made a capability out of a chore.

# Related

- [capability](/domain/capability.md) — why each is granted by its own premise rather than a
  pattern.
- [belief-base](/domain/belief-base.md) — where the beliefs it revises live, and the write
  boundary it respects.
- [self-review-is-a-capability](/decisions/self-review-is-a-capability.md) and
  [a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md).

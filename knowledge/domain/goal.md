---
type: Domain Concept
title: Goal
description: >-
  One thing wanted and how badly — the single shape a deliberator ranges over, whichever of the
  two sources it came from. A stake (a property of the subject this agent acts for) and a duty (a
  claim someone else holds against it) are deliberately the SAME type, so "my plant is dying" and
  "I owe fern a litre" finally rank against each other. Which kind it is is read off the data
  rather than a flag, because a flag that can disagree with the fields beside it eventually does.
  It carries its own STATE rather than inferring one from urgency: urgency is 0 only exactly at a
  region's centre, so "urgency > 0" once counted a comfortable barrel as unmet.
---

# What it is

A **goal** is one thing an agent wants, in the one shape a deliberator ranges over. It carries a
node of its own, an [urgency](/domain/urgency.md), and a state — plus whichever pair belongs to
its kind.

It is the **retired synonym's replacement**: *want* used to appear as a noun for this, and does
not any more. The verb is fine; the noun is `goal`.

# Two sources, one currency

A goal is either a **stake** — a property of the subject this agent acts for, wanted inside a
[region](/domain/region.md) — or a **duty**, an [obligation](/domain/obligation.md) someone else
holds against it.

They are deliberately the same type. An agent's whole conduct is things it wants, pursued through
[affordances](/domain/affordance.md), and a deliberator that had to ask which kind it was holding
would be the second decision path this design exists to avoid.

**Urgency is unit-free in both cases, and that is the whole point of the type.** A stake's comes
from the survival envelope — how much room is left before the subject ends; a duty's from the
redeem window — how much time is left before the claim expires. The two become comparable without
either knowing how the other was computed.

# The kind is read, never flagged

A stake carries what is wanted and what it currently reads. A duty carries the claim it came from
and whom it is owed to. **A stake has neither, which is what `is_duty` reads** — there is no kind
field, because a flag that can disagree with the data beside it is a flag that eventually does.

# State is carried, not inferred

A goal states its own condition in its kind's vocabulary: `met`, `unmet` or `unmeasured` for a
stake; `standing` or `demanded` for a duty.

**Carried rather than derived from urgency, and the distinction is not academic.** Urgency is 0
only exactly at a region's centre, so "urgency > 0" counts a barrel sitting comfortably inside its
range as unmet. It read that way on the bench for about ten minutes and made a calm society look
stuck.

A duty is never *met*. It is discharged — and a discharged debt is history rather than a goal.

# Wanted is not the same as actionable

`pursuable` is separate from urgency, and a duty nobody has presented is the case that needs it: it
stands, it may be hot, and it still must not be acted on. The holder is waiting for its own watch
to be live, and **a host that doses early spends the water where nothing is looking.**

Always true for a stake — a plant does not ask.

# It lives in the kernel

`agent/goal.py`, not in a package, because a goal is a **mental state** and those are the kernel's
— the same reason obligations and intentions are. Two packages need the type and neither may
import the other: [desire](/domain/desire.md) produces goals, [deliberation](/domain/deliberation.md)
consumes them, and the only thing they are allowed to share is a kernel word.

# Related

- [gap](/domain/gap.md) — where a stake's urgency comes from.
- [obligation](/domain/obligation.md) — the other source.
- [intention](/domain/intention.md) — what a goal becomes once the agent commits to closing it.

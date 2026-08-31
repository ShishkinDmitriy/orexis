---
type: Domain Concept
title: Act
term: http://example.org/orexis#Act
description: >-
  An action filled in — the lever it goes through, the want it serves, how much, for
  whom where it is an obligation, and WHEN: a window, not before and not after. Execution's word,
  where an action is a template: what an intention commits to, what an actor takes, what a
  commitment promises. Every act is an instance and no code names one; an action is the term
  it is an instance of.
---

# What it is

An [action](/domain/action.md) is a template — a precondition, an effect, a taker — and an
**act** is one filled in:

| | |
|---|---|
| action | which template — `market:Acquiring`, `actuation:Dosing`, … |
| lever | the [lever](/domain/lever.md) it goes through — this venue, this valve, this probe |
| want | the [desire](/domain/desire.md) it serves, and — `about` — what that want is about, opaque to the kernel |
| quantity | how much, sized by the taker (`size`) when the search fills the row — nothing, for a look |
| for | whom it serves, where it is an obligation's |
| window | **not before** and **not after** — when taking it counts |

The window is what makes it execution's word rather than planning's. A bid is an act *not
after* the round closes; a serve is an act *not after* the claim's `exp`; a look is an act *not
after* the auction that wanted it closes — every timer the actors keep by hand today is an
act's window kept somewhere else. *Not before* is the half nothing uses yet, and it is where a
held claim spent later — the futures seam in [claim](/domain/claim.md) — would arrive.

# Where it appears

- an [intention](/domain/intention.md) commits to an act — `orexis:by` names the act node, which
  `orexis:fills` the action and carries the lever (`orexis:through`), the quantity and the window;
- an [actor](/domain/actor.md) is handed one: `take(act, …)`;
- a [commitment](/domain/commitment.md) promises one — a [claim](/domain/claim.md) is a
  commitment to the host's Serving act for so many litres, not after `exp`;
- a [step](/domain/step.md) holds one, at its place in a plan, with what the search predicted.

# What it is not

**Not an affordance.** An [affordance](/domain/affordance.md) row is an action available now —
lever and want bound, nothing sized, no window — and the menu is derived on every ask. An act
is what a row becomes once the search sizes it (`Act.from_row`, in `Planner._step_from`) and
a commitment or a plan fixes when.

**Not a step.** A step is planning's: where an act sits in a plan and what the search thought
it would reach. The act is what survives the plan — committed, taken, promised.

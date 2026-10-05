---
type: Service
title: Executor
description: >-
  The owner of the intentions - it commits the plans a pass hands down, takes each step when it
  falls due, and moves an intention only when the world answers what the step predicted. Two
  doors, `tick` for time and `drain` for taking, called on one thread by the runtime and by a
  test alike. `agent/execution/executor.py`.
---

# What it does

- **`adopt`** — heard when planning publishes a [plan](/domain/planning/plan.md) — commits it as an
  [intention](/domain/execution/intention.md) that `execution:adopts` the plan by reference, standing at
  its first step; the plan stays planning's. It writes each step into the beliefs as a
  [committed step](/domain/execution/committed-step.md) over its landing window, closes the window when
  the step is answered or the intention ends, and `tick` forgets what has ended. A second plan for a
  want already standing is absorbed inside the patience and supersedes past it. **`end_for`** ends an intention that has taken no step
  `reached`, when planning says its want is met; **`end_at`** ends one `failed`, when planning says its
  next step is blocked; every intention that ends is an event planning hears
  ([planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).
- **`tick(now)`** hands every standing intention whose head [step](/domain/execution/step.md) is due
  — `execution:notBefore` past — to the queue, and for a head already taken asks whether the world
  answered. Where the world states a [resource](/domain/planning/constraint.md) — what an action
  `execution:occupies` — a due head is kept back for as long as an act of another intention holds
  the same thing, with nothing written of the wait; the elder intention's head goes first among those
  due at one instant.
- **`drain()`** takes each queued step and writes its [act](/domain/execution/act.md).

# Taking a step

In one order, read off the action's [implementation](/domain/execution/implementation.md):

1. an operation that reaches the world is carried out by a [signal](/domain/kernel/signal.md) of the
   executor's: an `execution:Command`'s payload by `commanded`, which execution's part hands the
   transport reaching the device, an `execution:Saying`'s document by `said`, for speech to believe and
   tell — order by order, each answered before the next;
2. a step marked `execution:keptBelow` is not taken fictively: it waits until planning has written
   the want that keeps it one level down, `execution:keptBy`, and is taken by recording that want
   `execution:refinedBy` on the act and waiting on it ([refinement](/domain/planning/refinement.md));
3. anything else is fictive: the executor writes the step's prediction into the state itself and
   the rules conclude of it, since nothing else would report it.

# The world answers

A taken step waits for its earliest landing, `execution:landsAt` — shifted by how late it was taken
— and then for the present, readings and their revisions, to hold every fact of the graph it
`execution:adds` and none of the one it `execution:retracts`, which is one `ASK` over the present with
the two graphs named. Then `execution:by` moves; the last step resolves the intention `done`.
Past its latest landing, `execution:notAfter`, by the patience with no answer, the intention
resolves `failed`, and the want is the search's again. A step kept below waits on the intention walking its want instead of the
clock, fails when that one does, and what hangs below an intention that ended undone is abandoned
with it.

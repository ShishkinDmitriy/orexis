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

- **`commit_plans`** takes up every [plan](/domain/planning/plan.md) handed down into the belief base —
  an `execution:PlanGraph` — and **`commit`** adopts each as an [intention](/domain/execution/intention.md),
  standing at its first step, tagging the steps' names so a second plan for one want never reuses
  the first's; the plan graph is forgotten. Nothing hands a plan over by a call
  ([planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).
- **`tick(now)`** hands every standing intention whose head [step](/domain/execution/step.md) is due
  — `execution:notBefore` past — to the queue, and for a head already taken asks whether the world
  answered.
- **`drain()`** takes each queued step and writes its [act](/domain/execution/act.md).

# Taking a step

In one order, read off the action's [implementation](/domain/execution/implementation.md):

1. an operation that reaches the world — an `execution:Command` sent to a device through the
   transport, an `execution:Saying` told to a peer — is carried out;
2. a step marked `execution:keptBelow` is not taken fictively: it waits until planning has written
   the want that keeps it one level down, `execution:keptBy`, and is taken by recording that want
   `execution:refinedBy` on the act and waiting on it ([refinement](/domain/planning/refinement.md));
3. anything else is fictive: the executor writes the step's prediction into the state itself and
   the rules conclude of it, since nothing else would report it.

# The world answers

A taken step waits for its landing, `execution:landsAt` — shifted by how late it was taken — and
then for the present, readings and their revisions, to hold every fact it `execution:predicts`
adds and none it retracts. Then `execution:by` moves; the last step resolves the intention `done`.
Past the landing by the patience with no answer, the intention resolves `failed`, and the want is
the search's again. A step kept below waits on the intention walking its want instead of the
clock, fails when that one does, and what hangs below an intention that ended undone is abandoned
with it.

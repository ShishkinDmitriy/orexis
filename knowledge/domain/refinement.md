---
type: Process
title: Refinement
description: >-
  A step kept one level down: where a step would be taken fictively, the Planner is asked whether
  some bridge concludes a fact the step predicts, and if one does, mints a want — the agent's own —
  whose met-test is the world the step lands in, regressed through the bridges. The step waits
  on that want's intention and fails when it does.
---

# What happens

The [executor](/domain/executor.md) reaches a [step](/domain/step.md). An action whose
implementation reaches the world — a command, a saying — is taken as it always was, whatever its
effect speaks: a dose predicts the soil inside its range, which sensing's rules conclude, and is
still a command. Only a step that would be taken fictively is handed to the Planner's `refine`,
which reads what the step predicts and looks for a [bridge](/domain/bridge.md) whose head
concludes any fact the step adds. None does — a drive, a pick — and the step is fictive. One
does, and the step is not the level's to take:

1. **The goal is the world the step lands in.** Every fact of a concluded predicate the present
   holds, less what the step retracts, plus what it adds — so the moved disk's new place AND
   every disk the step left alone.
2. **Each fact is regressed.** Its bridge's head is bound to the fact, and the bridge's WHERE,
   bound, is one way below to have it; where two bridges could conclude it, the ways are a
   UNION. The met-test is unmet while any fact has no way that holds.
3. **The want is the agent's own** — `planning:refines` the step, in a graph that arrived
   `orexis:Recorded` — and is placed in the [scope](/domain/scope.md) of what its met-test
   reads, planned there like any want, and walked by an intention of its own.
4. **The step waits on that intention**, recorded by `execution:refinedBy` on the act: while it
   stands, patience does not run. When it is done, the bridge concludes the step's fact of the
   present and the step is answered as any step is, off the readings and their revisions. When
   it ends undone, the step fails at once; and when the step's own intention ends undone,
   whatever walks the want below is abandoned with it.
5. **The want goes with its step.** Once no intention stands at the step it refines, the
   Planner forgets it, and what each imaginarium searched for it.

The whole plan above is found first, in the upper vocabulary alone, and each step is refined
only when its turn comes — from wherever the van then stands, not where it stood when the
puzzle was solved.

# Why the landing world and not the diff

Measured on the tower: with the added fact alone as the goal, `disk_1 on disk_2` was reached
below by carrying disk_2 over to disk_1, off the peg the plan above had put it on, and the
plan above walked on over a world it had not predicted. What the level above assumed of the
facts a step leaves alone is what its later steps stand on, so the level beneath is held to it.

# What it leaves open

A lower want no search can reach waits: the step above stands on an intention that is never
committed. What refuses such a step early — a relaxed reachability test at admission, and a
record of a refinement that failed, with a period — is the next change, and 0.1.0 had the
second as `refusedBelow`.

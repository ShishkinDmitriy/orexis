---
type: Process
title: Refinement
description: >-
  A step kept one level down: where a step would be taken fictively and some bridge concludes a fact
  it predicts, the Planner mints a want — the agent's own — whose met-test is the world the step
  lands in, regressed through the bridges. The want is minted ahead of the step's turn and begins
  where the plan below the step before it ends; the step waits on that want's intention and fails
  when it does.
---

# What happens

A [plan](/domain/planning/plan.md) is published, and some of its steps would be taken fictively. An
action whose implementation reaches the world — a command, a saying — is taken as it always was,
whatever its effect speaks: a dose predicts the soil inside its range, which sensing's rules
conclude, and is still a command. A step taken fictively whose predicted fact some
[bridge](/domain/planning/bridge.md)'s head binds is `execution:keptBelow`, said as the plan is
published; a drive or a pick, which no bridge concludes, is fictive
([planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).
A step kept below is not the level's to take, and the Planner gives it a want:

1. **The goal is the world the step lands in.** Every fact of a concluded predicate the present
   holds, with what each step still to be answered before it predicts applied in the order walked,
   less what the step retracts, plus what it adds — so the moved disk's new place AND every disk
   the step left alone.
2. **Each fact is regressed.** Its bridge's head is bound to the fact, and the bridge's WHERE,
   bound, is one way below to have it; where two bridges could conclude it, the ways are a
   UNION. The met-test is unmet while any fact has no way that holds.
3. **The want is the agent's own**, in a graph that arrived `orexis:Recorded`, beside
   `<step> execution:keptBy <want>` in execution's words, since the executor reads it — and is placed in the [scope](/domain/planning/scope.md) of what its met-test
   reads, planned there like any want, and walked by an intention of its own.
4. **The step waits on that intention**, recorded by `execution:refinedBy` on the act: while it
   stands, the step is not held to its landing. When it is done, the bridge concludes the step's
   fact of the present and the step is answered as any step is, off the readings and their
   revisions, within a patience of the intention's end. When it ends undone, the step fails at
   once; and when the step's own intention ends undone, whatever keeps a step of it below is
   abandoned with it, begun or not.
5. **The want goes with its step.** Once no plan still to be walked comes to the step it keeps,
   the Planner forgets it, and what each imaginarium searched for it.

# A step is refined ahead of its turn

The whole plan above is found first, in the upper vocabulary alone. The step an intention stands
at is given its want once it is due. Each step after it is given its own as soon as the plan below
the step before it is published — so the plan below a step is found while the steps before it are
still walked, and the executor takes a step once the plan below it exists, waiting for no other.

**Such a want begins where the plan before it ends.** Its graph holds from the instant that plan
ends, so it is weighed, as any want is, in the ground holding at its instant; and a ground is laid
there holding what the plans below still change — each untaken step's change applied over the ones
before, for the scope whose actions they fill. That ground is the state its search starts from:
where the van will stand, not where it stood when the puzzle was solved. When a plan ends is
computed at every planning off the plans and the intentions, never stored: a walk running late
moves every plan after it.

**A plan found ahead waits for the step it keeps.** The executor adopts it as it is published and
takes nothing of it until that step is taken, so two plans below are never walked at once.

**The present moves towards the ground, and the search goes on.** What a search imagined from a
ground ahead stays with that ground from one planning to the next while the ground and what is
read beside it stand ([cone](/domain/planning/cone.md)). Where the plan before goes otherwise than
it said, the ground is laid as another, and the want is searched again from it.

# Why the landing world and not the diff

Measured on the tower: with the added fact alone as the goal, `disk_1 on disk_2` was reached
below by carrying disk_2 over to disk_1, off the peg the plan above had put it on, and the
plan above walked on over a world it had not predicted. What the level above assumed of the
facts a step leaves alone is what its later steps stand on, so the level beneath is held to it.

# What it leaves open

A lower want no search can reach waits: the step above stands on an intention that is never
committed. Refined ahead, that is known before the step's turn comes, and nothing yet acts on it.
What refuses such a step early — a relaxed reachability test at admission, and a
record of a refinement that failed, with a period — is the next change, and 0.1.0 had the
second as `refusedBelow`.

A plan found ahead is placed at the instants the plans before it were to end at, so a walk that
runs ahead of its plan waits at each step below for the instant it was placed at.

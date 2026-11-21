---
type: Decision
title: The hierarchy is found in the rules a world combines
status: accepted
timestamp: 2026-09-26
description: >-
  Two domains planned one inside the other need no declaration of the hierarchy: a world that
  combines them states bridge rules, and a step whose predicted fact a bridge concludes is kept
  below by running the bridge backwards, ahead of its turn and from where the plan before it ends.
  Refused: a bridge declared per action, the rules run inside the search, a lower goal made of the
  step's diff alone, and the whole plan found before the first step.
---

# The hierarchy is found in the rules a world combines

The sovereign asked (2026-09-26) whether the core could decide by itself when to bridge, so
that combining two domains is enough, and whether the approach had a name. It does: a level
beneath a step is found by **goal regression** through **derived predicates** (PDDL's axioms,
here SHACL rules), the rules themselves are **bridge rules** in the multi-context systems'
sense, and planning the upper level whole and refining each step only when it comes up is
**Hierarchical Planning in the Now** (Kaelbling and Lozano-Pérez, 2011), with the BDI
intention stack as the execution side. The mechanism is [refinement](/domain/planning/refinement.md);
the rule it runs backwards is a [bridge](/domain/planning/bridge.md).

**The core decides, in one order, when it takes a step**: a step whose action has an
implementation that reaches the world — a command, a saying — is taken; one whose predicted
fact some bridge concludes is refined; anything else is fictive. Nothing marks an action
abstract. Move is fictive in hanoi's own world and refined in the tower's, because the tower
states a rule concluding `hanoi:on` and hanoi's world does not.

# What was refused

- **A bridge declared per action**, 0.1.0's: `orexis:Bridge` refining Move, with a CONSTRUCT
  translating the promised fact down and an estimate named beside it
  ([a-level-is-a-vocabulary-and-a-bridge](/decisions/0.1.0/a-level-is-a-vocabulary-and-a-bridge.md)).
  It worked, and it made the hierarchy an authored fact about ONE action: a second domain
  whose facts the courier could keep needed its own bridge per action, and the translation was
  a second statement of what the world's rules already said. A rule concluding `hanoi:on`
  from positions is needed anyway — the puzzle must be believed from where the disks stand —
  and running it backwards is the translation.
- **The rules run inside the search.** Every fork would then conclude `hanoi:on` from the
  van's moves, and one search over Moves and drives together is seven Moves as thirty-odd
  drives in one budget. The search runs no rules, the bridge couples no actions, and the two
  vocabularies are two [scopes](/domain/planning/scope.md), planned apart.
- **The step's diff as the goal below.** Measured before it was refused: the lower search met
  `disk_1 on disk_2` by moving disk_2, and the upper plan walked on over a world it had not
  predicted. The goal is the landing world's concluded facts — the frame, in the upper level's
  words.

# Amended 2026-11-19: a step is refined ahead of its turn, from where the plan before it ends

The record took Hierarchical Planning in the Now as it stands: the plan above whole, and each step
refined only when it came up. The sovereign's objection (2026-11-19) was to what that leaves
unknown: the agent started to act with no plan below any step but the first, and the van stood
still while each was searched. Measured on the two-disk tower the same day, it was worse than
that: a move was given its patience from its own landing, the drives below it took two minutes,
and the plan above failed and was found again after every move — three plans above where one was
owed, which the test, counting refinements, did not see.

So planning gives a step kept below its want ahead of its turn, and the want has an initial state
of its own. The step an intention stands at is refined when due, as before; each one after it as
soon as the plan below the step before is published. The want's goal is the world its step lands
in with the steps before it applied; it begins where the plan below the step before it ends — its
graph holds from that instant, and a ground is laid there holding what the plans below still
change — and it is searched from that ground as any want is searched from the ground at its
instant. The executor adopts the plan as it is published and takes nothing of it until the step it
keeps is taken; a step kept below is given its patience from the end of the plan below it. The
mechanism is on the [refinement](/domain/planning/refinement.md) page. On the tower the plan above
is found once and walked to its end, and the plans below the second and third moves are found
while the first is driven.

What was refused:

- **The whole plan before the first step.** Nothing would then be taken on a plan that cannot be
  finished below. It puts every search before the first drive — seven on the three-disk tower —
  where searching and walking overlap, and a surprise partway redoes the rest. The sovereign chose
  a step taken once the plan below it exists.
- **A figure on the planner's role for how far ahead a step must be planned below.** One step
  ahead and all of them are the two cases above, and nothing asked for a third.
- **The want begun in a possible world**, the last of the plan before it, in the scope's
  imaginarium. No ground would be laid, and the search would continue the cone that found the
  plan before. But a cone is dropped as the present moves, and a want begun in a world the
  imaginarium no longer holds begins nowhere; the steps of a published plan are in the beliefs,
  so a ground is laid from them at every planning.
- **Every untaken step of every walking plan laid into the grounds ahead**, as a step in flight
  is. A later want would then see the whole plan before it, in every world; it is a ground per
  step of every plan, weighed for every desire, where one ground at the instant a want begins is
  what a search needs.

Three things the change found in what it stood on, each fixed with it and said on the
[cone](/domain/planning/cone.md) page: a world weighed for a want that has not begun was taken
for the present; the ground a want began at, laid by one planning and not by the next, went on
holding for ever; and what stands beside a ground was asked before the changeable was cut out of
it, so no ground laid again during a walk kept what was imagined from it. The second is fixed for
those grounds alone: taken back for every ground laid ahead, the lane's two couriers no longer
parted, so a ground a landing or a forecast laid and the next planning did not still stands, and
the lane's walks depend on it — a debt, not a decision.

# Seams left open

- **A plan found ahead is placed at the instants the plans before it were to end at.** A walk that
  runs ahead of its plan waits at each step below for the instant it was placed at; one running
  late is followed, since where each plan ends is computed at every planning.
- **On several threads, a search ahead is dropped where the walk moved what crossed into it**, by
  the rule of [the-agent-is-a-runtime-of-tasks](/decisions/the-agent-is-a-runtime-of-tasks.md),
  and planning is due again. What it imagined stays with its ground, so the next search goes on
  from it; a rule that counts the present as still on the plan towards that ground is not built.
- **A refinement the lower level cannot reach** waits rather than fails. Refined ahead, it is
  known before the step's turn, and nothing yet acts on it. A relaxed test at
  admission (delete relaxation over the lower actions) and a failed-refinement record with a
  period are the design; neither is built.
- **The lower want carries no estimate**, so its search is uniform-cost and the three-disk tower
  takes two and a half minutes on the Pi; the gate runs two disks.
- **A bridge is one head triple.** A rule concluding two facts at once, or binding its head
  with `BIND`, is not run backwards.

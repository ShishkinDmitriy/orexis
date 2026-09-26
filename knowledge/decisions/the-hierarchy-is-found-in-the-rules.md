---
type: Decision
title: The hierarchy is found in the rules a world combines
status: accepted
timestamp: 2026-09-26
description: >-
  Two domains planned one inside the other need no declaration of the hierarchy: a world that
  combines them states bridge rules, and a step whose predicted fact a bridge concludes is kept
  below by running the bridge backwards. Refused: a bridge declared per action, the rules run
  inside the search, and a lower goal made of the step's diff alone.
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

# Seams left open

- **A refinement the lower level cannot reach** waits rather than fails. A relaxed test at
  admission (delete relaxation over the lower actions) and a failed-refinement record with a
  period are the design; neither is built.
- **The lower want carries no estimate**, so its search is uniform-cost and the three-disk tower
  takes two and a half minutes on the Pi; the gate runs two disks.
- **A bridge is one head triple.** A rule concluding two facts at once, or binding its head
  with `BIND`, is not run backwards.

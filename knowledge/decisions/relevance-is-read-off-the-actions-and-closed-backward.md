---
type: Decision
title: Relevance is read off the actions and closed backward
description: >-
  #488's decision. Which levers a pass simulates for a want is derived per pass from the
  want's shape and the actions' own texts — what a want reads, what an action writes and
  reads — closed backward through preconditions and derivation rules to a fixed point, with
  anything unreadable keeping every action. Refused: a declared `orexis:touches` on actions (a
  second statement of what the construct settles); filtering to actions that touch the goal
  without the closure (deletes every chain); reasoning modelled as search actions (a free
  state-changing row is the exact case that multiplies forks, and an entailment is a
  computation, not a step — it is an edge here and saturation for the search); the relevance
  set written to a derived graph at genesis (it depends on a want review rebuilds, and what
  the interpreter already knows is computed, never asserted).
status: accepted
timestamp: 2026-09-02T18:00:00Z
---

# Relevance is read off the actions and closed backward

A pass simulated every row on the menu, and a row that names no want reaches every pass. One
free foreign action multiplied a three-disk solve 2.8 times when the runbook first measured it,
and since [a-pass-is-budgeted-in-worlds](/decisions/a-pass-is-budgeted-in-worlds.md) the same
lever does worse than slow the solve: it spends the budget on worlds the want cannot be met in,
and the pass answers EXHAUSTED with three moves where seven solve it. Neither the cost bound
nor cycle detection can see it — a free action lets every descendant tie, and a world that
genuinely changed is somewhere new. What sees it is the question this record answers: does
this lever touch anything the want reads?

The answer is DERIVED from what already exists. A want's shape carries its paths; an action's
effect carries its template; an action's precondition carries its patterns. Relevance is the
backward closure of the three, and it is the closure that matters: filtering to actions that
touch the goal predicates would keep a dose and delete the bid that makes it possible. A
derivation rule is an edge in the same closure, and a sub-property widens the want's reads the
way the entailment would. All of it is computed per pass and parsed once per text, and none of
it is written down.

# What was refused

**A declared `orexis:touches`.** The obvious form: each action says which predicates it touches,
and the search filters on the declaration. Refused because it is a second statement of a fact
the construct settles, and a second statement can disagree with the first — `planner.py`
carries the scar of `orexis:confirmedBy`, a guard that matched every lever and made the search
depth-1 whatever the constant said.

**Filtering without the closure.** Actions whose effect touches the goal, and no more. It deletes
every chain: in the plant world a moisture want is served by bid, apply, dose, and only the
last touches an observation. The closure brings the bid in on the second round through the
dose's precondition, and stops.

**Reasoning as a search action.** The sovereign's idea, and the intuition is right for
relevance and wrong for the search. A rule as a menu row is a free action that changes state,
which is the knob case exactly, inside the one pass where the rule counts; and where the rule
is relevant, applying it never hurts and not applying it never helps, so branching on it is a
computation spent as a fork. The search's answer is saturation — each possible world closed
under the relevant rules before it is scored, PDDL's derived predicates — and relevance's
answer is the edge this record builds. What IS an action is the expensive or fallible kind of
reasoning: a model consulted, a look taken. Both are already rungs.

**Writing the set to a derived graph at genesis.** Proposed in the issue and refused when the
shape compiler landed: the set depends on the want's shape, which review rebuilds, so a
genesis-written triple goes stale; and anything the interpreter already knows is computed,
never asserted. What is visible instead is the trace, which names every row the filter passed
over.

# Seams left open

- **Saturation.** Derived predicates are not applied to possible worlds yet, so an action
  relevant only through a rule's edge is kept by relevance and cannot yet meet the want in
  the search. The edge is built and tested at the set level; the fixpoint per node is #108's,
  with its cost to measure.
- **A finer key.** Predicates alone: two domains sharing one predicate stay mutually relevant.
  A (predicate, subject class) key is the refinement, when a world shows the cost.
- **Plant levers read as writing anything**, because their retraction template is
  `?obs ?p ?o`. The sound reading, and the reason relevance filters nothing in a plant world
  today; a retraction that names the observation's predicates would let it.

# Issues this closes

[#488](https://github.com/ShishkinDmitriy/orexis/issues/488).

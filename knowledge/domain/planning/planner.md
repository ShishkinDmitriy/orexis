---
type: Service
title: Planner
description: >-
  The service that runs a pass - derive the wants, then for each a bounded best-first search over
  possible worlds, ordered by what a path spent plus what the want's estimate says is left, and
  the plans handed to the executor. The one name the rest of the tree imports from planning;
  every act it sequences starts in the store and ends in it. `agent/planning/planner.py`.
---

# A pass

`Planner.plan(at)` runs once per [runtime](/domain/kernel/runtime.md) pass, and per
[scope](/domain/planning/scope.md) of the store:

1. refresh the scope's [imaginarium](/domain/planning/imaginarium.md) and lay its grounds, then
   re-root the kept [cone](/domain/planning/cone.md) on the present;
2. weigh every desire in every ground and derive the wants from what reads unmet; withdraw what no
   longer does, and every want met in the present ([desire](/domain/planning/desire.md));
3. search each want of the scope that no intention is already walking;
4. hand the plans down (`publish_plan`).

# A search

`search(want)` weighs the ground, then calls `expand` until the frontier is empty, the cheapest
achiever refuses the top, or the [budget](/domain/planning/budget.md) is spent. `expand` opens the
cheapest open world: `admit` writes the candidates its [preconditions](/domain/planning/precondition.md)
allow, among the scope's actions only; `take` forks each into a world and runs its
[effect](/domain/planning/effect.md); `weigh` judges the world by the want's met-test and writes
`planning:met`, `planning:open`, `planning:spent` and `planning:remaining`, and judges it by each
state [invariant](/domain/planning/constraint.md) of the holder the scope's actions can write, so a
world that newly enters an avoided state is `planning:refused` and taken off the frontier. The
frontier is a query over those rows — A\* by reading them — so a search called again takes up where
it stopped. `extract_plan` then writes the [plan](/domain/planning/plan.md).

# Its shape

A star, not a chain: the Planner sequences the acts as its own methods, and no act calls another —
what one needs of another's work it reads off the rows the other wrote. It calls the executor
nowhere either: a plan goes down into the belief base, what is walked is read off the intentions
there, and a step a bridge keeps below is marked when published and given its want when due
([refinement](/domain/planning/refinement.md)).

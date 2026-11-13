---
type: Domain Concept
title: Budget
description: >-
  How much one call may spend, stated in the unit the work spends - candidates weighed for a
  search, rule executions for revision. Each call's own and a ceiling on latency, not on the
  problem - work a budget cut short stays where it was and the next pass continues it.
---

# The two budgets

- **The search's**, in candidates weighed: `planning:budget`, a [stance](/domain/kernel/stance.md)
  the Planner reads when it is made, or `Planner(budget=…)` where a caller sizes one. A
  search stops when it has weighed that many more than it had, and its plan says
  `planning:Exhausted`. The frontier is rows, so the next planning opens the same worlds where this
  one stopped: three disks at twenty a planning reach their seven moves on the third, having
  weighed exactly what one planning with room would.
- **Revision's**, in rule executions: the [deliberator](/domain/belief/deliberator.md)'s per pass,
  `belief:budget`, a stance too. A graph the budget cut short keeps what was concluded, its row saying `belief:settled false`.

# A budget is for a stretch of time

A search the budget cut short is given its next budget when one of two things holds, and not before:
the grounds it is searched in differ from those it was cut short in, by their hashes, which is news;
or `planning:budgetEveryS` of the agent's time has passed since it was cut short, a stance too, ten
seconds where none is stated. The planner says when that is (`continues_at`), and planning's
[policy](/domain/kernel/policy.md) wakes then.

The pair is what makes the budget a ceiling: so many candidates per so many seconds. While the runtime
was a pass, the pass was the period, one budget each. With each package a task that begins on what it
hears, every event heard began a planning, and each planning handed the same search a fresh budget:
the lane's two couriers, first hearing each other, ran one search to its budget nineteen times at one
instant, with nothing new to search in sixteen of them.

# Why this unit

A ceiling on compute is stated in the unit the work spends. Depth was that unit under
breadth-first and stopped being it under best-first; a number of worlds is what a world's author
can size from a measured cost per fork, and is what a pass actually pays.

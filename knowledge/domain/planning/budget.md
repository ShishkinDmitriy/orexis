---
type: Domain Concept
title: Budget
description: >-
  How much one call may spend, stated in the unit the work spends - candidates weighed for a
  search, rule executions for revision. Each call's own and a ceiling on latency, not on the
  problem - work a budget cut short stays where it was and the next pass continues it.
---

# The two budgets

- **The search's**, in candidates weighed: `Planner(budget=…)`, the runtime's `--budget`. A
  search stops when it has weighed that many more than it had, and its plan says
  `planning:Exhausted`. The frontier is rows, so the next pass opens the same worlds where this
  one stopped: three disks at twenty a pass reach their seven moves on the third pass, having
  weighed exactly what one pass with room would.
- **Revision's**, in rule executions: the [deliberator](/domain/belief/deliberator.md)'s per pass.
  A graph the budget cut short keeps what was concluded, its row saying `belief:settled false`.

# Why this unit

A ceiling on compute is stated in the unit the work spends. Depth was that unit under
breadth-first and stopped being it under best-first; a number of worlds is what an operator can
size from a measured cost per fork, and is what a pass actually pays.

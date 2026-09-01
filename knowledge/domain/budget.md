---
type: Domain Concept
title: Budget
term: http://example.org/orexis#budgetWorlds
description: >-
  How much one pass of the search may imagine, counted in possible worlds — the ceiling on
  what a deliberation spends, stated in the unit it spends. A pick the sovereign authors in
  the agent's beliefs, bounded by a kernel shape, never moved by the agent; the engine keeps a
  default where none is stated. Not the wallet, which is what an agent has; a budget is what
  one pass may use up, and the pass answers with its best when it does.
---

# What it is

`orexis:budgetWorlds`, an integer on the agent in its own beliefs, authored in
`world/<world>/beliefs/` beside the patience. One pass of the [planner](/domain/planner.md)
forks at most that many worlds in the [imaginarium](/domain/imaginarium.md) and then answers
with the best it holds: the cheapest achiever found, or the world nearest the want by the
want's own [estimate](/domain/desire.md), or the finding that nothing helps. The search is
anytime by construction — it keeps its best as it goes — so a spent budget is an answer, never
an absence of one.

# How to use it

**State it in worlds, and size it from the runbook.** A world costs what the mutable slice
makes it — a few milliseconds at a handful of triples, tens at ten thousand
([measure-the-search](/runbooks/measure-the-search.md)) — so the same number is a different
number of seconds on different worlds, and that is the point of stating it in this unit: the
sovereign says how much imagining, and the world says what imagining costs.

**Leave it out where the default serves.** `Planner.BUDGET` is sized for a plant, whose pass
forks a handful, and it solves two disks of hanoi but not three. `world/hanoi` states 64 and
`world/courier` 128 because their solves need it; no plant world states one.

**It is not a depth.** A depth bounds how far ahead a plan may reach, which nothing needs — a
plan is re-derived every pass and only its head is acted on — and under a best-first search
it does not bound compute at all. Why the unit changed is
[a-pass-is-budgeted-in-worlds](/decisions/a-pass-is-budgeted-in-worlds.md).

**It is not the [wallet](/domain/wallet.md).** The wallet is a balance the agent holds; a budget
is what one pass may use up. The day thinking is metered, a pass's worlds are what the wallet
is charged for, and the two words meet there and nowhere earlier.

**Bounded, not demanded.** `orexis:BudgetShape` holds a stated budget to one integer between 1
and 1024 and refuses the world otherwise — zero is an agent that never thinks and looks calm
— but demands none, unlike the patience `orexis:KeeperShape` requires of every stake.

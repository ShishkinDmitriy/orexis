---
type: Domain Concept
title: Step
term: http://example.org/orexis#Step
description: >-
  One act at its place in a plan. On the search's side, with what the search predicted taking
  it would reach; in the ledger, what an intention stands at — it takes the act, waits for a
  condition if it has one, says what happens if the wait lapses, and may name the step that
  follows. A weighed step that was not chosen is a candidate in the trace.
---

# What it is

A **step** is an [act](/domain/act.md) at a position in a plan: its order, and what the
search predicted — the urgency the want would have in the world after it (`urgency_after`).
`Plan.steps` holds them (`packages/orexis-agent-progression/act.py`'s `Step`); the [imaginarium](/domain/imaginarium.md)
holds the world each one reached, for the life of one pass, and names that world by the path
of steps that reached it.

# In the ledger

`orexis:Step`, since #514. An intention stands at a step (`orexis:at`); the step takes the act
(`orexis:takes`); and the step is where readiness lives — `orexis:until` or `orexis:untilNot`,
a shape it waits for, and `orexis:whenLapsed`, what the keeper does if the deadline passes
first. The intention is the commitment, the act is the doing, the step is the place: three
words because three readers ask three questions. `orexis:then` names the following step and is
[#510](https://github.com/ShishkinDmitriy/orexis/issues/510)'s to write: a plan handed down
whole is a chain of steps, each held until the previous one's expectation conforms.

# Only the head is committed

The plan is re-derived every pass because the world moves, so a committed tail would be a
promise about a future nobody has seen. [Execution](/domain/executor.md) takes the first
step's act, hands it to the keeper as an [intention](/domain/intention.md), and the rest is
trace: every step weighed is an `orexis:Candidate` in the deliberation graph, chosen or not, and
none of it is read back.

# What it is not

**Not an act.** The act is what the step proposes; it survives the plan when committed. The
step does not — it is a hypothesis about a world, and a hypothesis must survive nothing
([imaginarium](/domain/imaginarium.md)).

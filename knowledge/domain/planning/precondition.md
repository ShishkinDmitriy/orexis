---
type: Domain Concept
title: Precondition
term: http://example.org/orexis/planning#precondition
description: >-
  When an action may be taken - a SELECT over a world binding one variable per parameter the
  action takes, whose rows are the steps that world admits. Zero rows is ordinary, many is the
  choice the search makes. Asked of the present again to learn whether a step still applies, so
  no step keeps a copy of what it read.
---

# What it is

`planning:precondition` on an [action](/domain/kernel/action.md): a select naming no graph, whose
projected variables are the local parts of what the action `orexis:takes`, asking for the agent as the
[self](/domain/kernel/self.md), `?me a orexis:Self`, and handed nothing. `admit` runs it in a world through
`world_at` — the world's own graphs, every public one and the beliefs, the self's among them —
and writes a `planning:Candidate` per row: the world it leaves, the action it fills, and a triple per
parameter under the parameter's own IRI.

A precondition is the query, whole. It says which disk may move onto which peg, which van may drive
to which neighbouring cell, which venue has a round open to tender into; nothing else in the
action restates it.

# What a step does not carry

A [step](/domain/execution/step.md) keeps no copy of what its precondition read in the world it was
planned from. Whether a step an intention stands at can still be taken is asked of the present, as
the executor is about to take it, by running the action's precondition there again (`Planner.check`,
#916), and a row carrying the step's own filling is the answer; a stored copy of the facts the search read was declared once, written by
nothing, and retired
([a-steps-prediction-is-two-graphs-it-names](/decisions/a-steps-prediction-is-two-graphs-it-names.md)).

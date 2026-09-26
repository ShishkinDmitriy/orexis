---
type: Domain Concept
title: Precondition
term: http://example.org/orexis/planning#precondition
description: >-
  When an action may be taken - a SELECT over a world binding one variable per parameter the
  action takes, whose rows are the steps that world admits. Zero rows is ordinary, many is the
  choice the search makes. A step carries what its rules read there, as facts, beside what it
  predicts.
---

# What it is

`planning:precondition` on an [action](/domain/kernel/action.md): a select naming no graph, whose
projected variables are the local parts of what the action `orexis:takes`, with `$me` for the agent
asking. `admit` runs it in a world through `world_at` — the world's own graphs and every public one —
and writes a `planning:Candidate` per row: the world it leaves, the action it fills, and a triple per
parameter under the parameter's own IRI.

A precondition is the query, whole. It says which disk may move onto which peg, which van may drive
to which neighbouring cell, which venue has a round open to tender into; nothing else in the
action restates it.

# What a step carries

When a plan is extracted, each step carries `execution:precondition`: the positive patterns its
precondition and its effect read, instantiated for its filling in the world it was planned from,
as the same canonical facts its prediction is made of. It is the step's premise, kept with it.

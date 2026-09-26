---
type: Domain Concept
title: Step
term: http://example.org/orexis/execution#Step
description: >-
  An action picked for execution, with the values it was filled with - what a plan is made of.
  Carries the action it fills, a triple per parameter, what the search predicted it changes, what
  its rules read, when it may be taken and when its change will have landed. A world merely admits
  candidates; the search picks, and a picked candidate is a step.
---

# What it is

A world ADMITS one candidate per action per row of its precondition; the search forks the ones
it opens, and the candidates on the winning world's ancestry become steps. So a step is a
candidate that was picked, and adds at least the values it was picked with:

| | |
|---|---|
| `planning:fills` | the [action](/domain/kernel/action.md) |
| a triple per parameter | under the parameter's own IRI — `hanoi:disk :disk_1`, `hanoi:onto hanoi:PegC` |
| `execution:predicts` | the change: the canonical facts its world gains and loses (`adds`, `retracts`) |
| `execution:precondition` | what its rules read there ([precondition](/domain/planning/precondition.md)) |
| `execution:notBefore` | the instant of the world it is taken in — a requirement |
| `execution:landsAt` | when its change is complete, off the action's `planning:landsAfter` |
| `execution:then` | the next step of the plan |

# How it is taken

An [intention](/domain/execution/intention.md) stands at one step at a time. When it falls due the
[executor](/domain/execution/executor.md) takes it — by command, by saying, kept below, or fictively
— writes an [act](/domain/execution/act.md), and holds the world to what it predicted. The
kernel reads no value bound to a parameter; a domain's texts read them as `$tokens`, which is why a
parameter's local part is its variable, its token and its predicate at once.

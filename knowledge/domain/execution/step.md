---
type: Domain Concept
title: Step
term: http://example.org/orexis/execution#Step
description: >-
  An action picked for execution, with the values it was filled with - what a plan is made of.
  Carries the action it fills, a triple per parameter, the two graphs holding what the search
  predicted it changes, when it may be taken and when its change will have landed. A world merely
  admits candidates; the search picks, and a picked candidate is a step.
---

# What it is

A world ADMITS one candidate per action per row of its precondition; the search forks the ones
it opens, and the candidates on the winning world's ancestry become steps. So a step is a
candidate that was picked, and adds at least the values it was picked with:

| | |
|---|---|
| `planning:fills` | the [action](/domain/kernel/action.md) |
| a triple per parameter | under the parameter's own IRI — `hanoi:disk :disk_1`, `hanoi:onto hanoi:PegC` |
| `execution:adds` | the graph of facts its world gains — an `execution:AddsGraph`, stated and not believed |
| `execution:retracts` | the graph of facts its world loses — an `execution:RetractsGraph` |
| `execution:notBefore` | the start of the period of the world it is taken in — a requirement |
| `execution:landsAt` | the earliest the world can show its change — the least the action's `planning:landsAfter` says |
| `execution:notAfter` | the latest — the most it says, summed along the plan; a dose's a cadence past the step, since its sensor's next reading is due within one |
| `execution:then` | the next step of the plan |

# What it predicts

What its action's [effect](/domain/planning/effect.md) changed in the world it was applied to, and
nothing else, as two graphs named `<step>.adds` and `<step>.retracts`, which the engine fills when
the plan is extracted. Where the world the step reaches was forked from the world it leaves, that is
the diff of the two; where it was forked from the later ground the step lands in, the two also
differ by what the predictions moved between their periods — another van's next cell — which is no
part of the step (#919). Their kinds
are beneath `orexis:Graph` alone, so a reader of the present is never handed them: a world where the
dose has landed is not this world
([a-steps-prediction-is-two-graphs-it-names](/decisions/a-steps-prediction-is-two-graphs-it-names.md)).
They travel with the plan when it is published and go when it goes. What a step's rules read in the
world it was planned from is not kept with it; whether a step still applies is asked of the present
with the action's own [precondition](/domain/planning/precondition.md).

# How it is taken

An [intention](/domain/execution/intention.md) stands at one step at a time. When it falls due the
[executor](/domain/execution/executor.md) takes it, unless the present no longer admits it — checked
at that moment, whether it fell due at a pass's start or inside a walk — by command, by saying, kept
below, or fictively; writes an [act](/domain/execution/act.md), and holds the world to what it predicted, from the
earliest landing to a patience past the latest. The
kernel reads no value bound to a parameter; a domain's texts read them as `$tokens`, which is why a
parameter's local part is its variable, its token and its predicate at once.

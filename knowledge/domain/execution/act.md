---
type: Domain Concept
title: Act
term: http://example.org/orexis/execution#Act
description: >-
  The record that a step was taken - which step, when the taker was handed it, when it returned,
  and whether it was taken at all. History, and only history - the world says whether the step's
  change landed, through a reading, never the act.
---

# What it is

```turtle
:act_… a execution:Act ; execution:of :step ;
    execution:takenAt "…"^^xsd:dateTime ; execution:doneAt "…"^^xsd:dateTime ;
    execution:taken true .
```

Written by the [executor](/domain/execution/executor.md) in the intentions graph as the step leaves
flight. `execution:taken false` is an attempt no taker could carry out — the command raised — and
the intention fails with it. A step kept one level down carries `execution:refinedBy` the want it
became, and waits on that want's intention.

# What it is not

Not the step: a [step](/domain/execution/step.md) is planned and may never be taken; an act is what
happened when it was. And not the change: `takenAt` and `doneAt` are how long the taking took, and
when the change is complete is the step's `execution:landsAt`, answered by the world.

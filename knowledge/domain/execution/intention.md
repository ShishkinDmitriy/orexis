---
type: Domain Concept
title: Intention
term: http://example.org/orexis/execution#Intention
description: >-
  A commitment to one plan for one want - adopted at an instant, standing at a step, resolved at
  another instant as done, failed or abandoned. Rows in the executor's intentions graph, so a
  restart finds every intention where it stood; the I of BDI, and the only thing a pass leaves
  that outlives it.
---

# What it is

```turtle
:intention_mover_91b8c43d a execution:Intention ;
    execution:pursues :every_disk_home ;
    execution:adoptedAt "…"^^xsd:dateTime ;
    execution:step :s1 , :s2 , :s3 ;
    execution:by :s2 .
```

`execution:pursues` is the want, `execution:step` every step of the plan, `execution:then` their
order and `execution:by` the one it stands at now. `execution:resolvedAt` and `execution:outcome`
are absent while it stands: their absence is the standing state.

# How it moves

The [executor](/domain/execution/executor.md) moves it and nothing else writes it: `by` advances when
the world holds what the step predicted, and the intention resolves `done` at the last step,
`failed` when the world did not answer within the patience or a step kept below could not be
kept, and `abandoned` when the intention a step of it was kept below for ended undone.

# What it means for the search

A want an intention walks is neither searched again nor handed a second plan: the world has not
answered yet, and deciding again is the executor's verdict on a step, never the clock's. When it
fails, the want is the search's again, from wherever the world then stands.

# Several at once

An agent may stand in several intentions — a supplier serving two claims, a tower's upper plan and
the courier plan refining its current Move. Each walks its own want; the one link between them is
the act that a step was kept below, and failure travels along it upward, abandonment downward.

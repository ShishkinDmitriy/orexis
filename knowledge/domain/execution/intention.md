---
type: Domain Concept
title: Intention
term: http://example.org/orexis/execution#Intention
description: >-
  A commitment to one plan for one want - adopted at an instant, standing at a step, resolved at
  another instant as done, failed, superseded or abandoned. Rows in a graph of the belief base, the agent's own
  and not public, so a restart finds them where they stood; the I of BDI, and the only thing a pass
  leaves that outlives it.
---

# What it is

```turtle
:intention_mover_91b8c43d a execution:Intention ;
    execution:pursues :every_disk_home ;
    execution:adoptedAt "…"^^xsd:dateTime ;
    execution:step :s1 , :s2 , :s3 ;
    execution:by :s2 .
```

`execution:pursues` is the want, `execution:adopts` the [plan](/domain/planning/plan.md) it commits to —
planning's, published once and referred to, never copied — `execution:step` every step of that plan,
and `execution:by` the one it stands at now; the steps' order, `execution:then`, is read in the plan. `execution:resolvedAt` and `execution:outcome`
are absent while it stands: their absence is the standing state.

# How it moves

The [executor](/domain/execution/executor.md) moves it and nothing else writes it: `by` advances when
the world holds what the step predicted, and the intention resolves `done` at the last step,
`failed` when the world did not answer within the patience, a step kept below could not be kept,
or planning said its next step is blocked in the present, `reached` when planning said its want is
met before any step was taken, `superseded` when a reconsideration replaced its untaken steps — after
its step in flight is answered, `execution:endsAfter` — and `abandoned` when the intention a step of
it was kept below for ended undone. A plan that has begun is not ended because its want is met partway.

# What it holds the agent to

Its [commitment](/domain/execution/commitment.md): the step in flight is never cancelled, and the plan
is kept until one of commitment's two triggers reopens the want it pursues. When it ends, planning hears it and the
want is the search's again at once, from wherever the world then stands.

# Several at once

An agent may stand in several intentions — a supplier serving two claims, a tower's upper plan and
the courier plan refining its current Move. Each walks its own want; the one link between them is
the act that a step was kept below, and failure travels along it upward, abandonment downward.

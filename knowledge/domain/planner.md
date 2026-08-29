---
type: Service
title: Planner
description: >-
  The service that runs planning — a bounded breadth-first search over simulated worlds, ranking
  each by the urgency the want would have there. It reads the action templates and every graph a
  premise may touch, writes one possible world per node it reaches, and returns a plan it never
  stores. The only service whose two outputs are one modality: the worlds die with the pass and
  the trace survives it.
---

# What it runs

**Planning.** Given one [desire](/domain/desire.md), walk the [affordance](/domain/affordance.md)
rows the [menu](/domain/menu.md) yields, simulate each by applying its
[effect](/domain/effect.md) to the world reached so far, and rank the results by urgency. Bounded
depth, breadth-first, so siblings are alive at once — which is why a world is a value rather
than a mutable state.

# What it reads and writes

```mermaid
flowchart LR
  subgraph BEL["Beliefs · repository"]
    A["ag:ActionGraph"]
    W["ag:WorldGraph"]
    S["ag:StateGraph"]
    P["ag:PickRecordGraph"]
    O["ag:ObligationsGraph"]
    D["ag:DeliberationGraph"]
  end
  subgraph DES["Desires · repository"]
    X["no graph class"]
  end
  subgraph IMG["Imaginarium · repository"]
    V["ag:PossibleGraph"]
  end
  PL["Planner<br/>runs Planning"]
  A -. reads .-> PL
  W -. reads .-> PL
  S -. reads .-> PL
  P -. reads .-> PL
  O -. reads .-> PL
  X -. reads .-> PL
  V -. reads .-> PL
  PL -- writes --> V
  PL -- writes --> D
```

**One service, one output modality.** `ag:DeliberationGraph` is a subclass of
`ag:PossibleGraph`, so both writes are possible-modality: the worlds that die with the pass, and
the trace that survives because the health series read it.

# What it is not

**Not the decider.** [Deliberation](/domain/deliberation.md) chooses whether to pursue at all and
calls this; [execution](/domain/execution.md) commits the head. The plan itself is returned and
never stored — it is [required to be lost](/decisions/there-is-no-bdi-ontology.md).

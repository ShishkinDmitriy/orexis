---
type: Domain Concept
title: Committed step
term: http://example.org/orexis/execution#CommittedStepGraph
description: >-
  A step an intention has adopted, believed over its landing window - from the instant it may be
  taken to a patience past the latest it may land. One graph per step, written by the executor at
  adoption and closed when the step is answered or its intention ends, so that a drift reads what
  the agent is about to do and a prediction made afterwards contains the plan.
---

# What it is

```turtle
GRAPH <…/committed/grower/plan_s1> {
    :plan_s1 a execution:Step ;
        planning:fills actuation:Dosing ; actuation:valve :pump ; actuation:reading :obs_bed ;
        execution:landsWithinS 600 ; execution:answeredWithinS 660 .
}
```

The catalogue says the graph is an `execution:CommittedStepGraph`, a belief, holding from the step's
`execution:notBefore` to its `execution:notAfter`, the latest landing, plus the patience. Inside is
the step's filling, copied from the [plan](/domain/planning/plan.md) as terms the executor never
reads, and two numbers of the executor's own: `execution:landsWithinS`, how many seconds after its
opening the change lands at the earliest, and `execution:answeredWithinS`, how many until the
window closes. They are numbers
because the engine binds nothing for the stretch between two instants, so a rule dividing a rise by
the window could not take it from the instants on the step.

# Why it is a belief

An [intention](/domain/execution/intention.md) is the agent's own and crosses into no possible world;
what a [drift](/domain/prediction/prediction.md) may read at an instant is a public or belief graph
holding then. A committed step is the one row of an intention written as a belief, so the dose the
grower is about to give is a flow its bed's prediction accumulates — rising to the aim over the
window, on the low trajectory by the latest landing — and a want searched after the adoption sees a
future that contains the plan, which is the IRMA order: a commitment is background a new option is
filtered against
([a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md)).
The window's two ends are happenings of every prediction, and prediction learned no word of
execution's: it hears every belief written and rewrites each key's stretches when the one written is
no sensor's observation.

# Not the prediction

The two graphs a step predicts in, `execution:adds` and `execution:retracts`, stay the
[plan](/domain/planning/plan.md)'s and are never copied here. They differ from this graph in
modality — stated against believed — and in lifetime — the plan's against the window's; put in a
belief graph, "the soil is inside its range" would be handed to every met-test from the moment of
adoption, and the want would read met before the world answered
([a-steps-prediction-is-two-graphs-it-names](/decisions/a-steps-prediction-is-two-graphs-it-names.md)).

# How it ends

The [executor](/domain/execution/executor.md) closes the window at the instant the world answers the
step, and every window of an intention at the instant the intention resolves — superseded, failed or
abandoned, the untaken steps' with their whole stretch ahead. A reconsideration closes the untaken
steps' windows when it is heard, before its intention ends after the step in flight
([commitment](/domain/execution/commitment.md)). Closing is a write, heard as one; what
has ended is forgotten on the next tick, told to nobody, since a graph past its end is handed to no
reader asking at a later instant.

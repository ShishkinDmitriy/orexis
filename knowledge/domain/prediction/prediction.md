---
type: Domain Concept
title: Prediction
term: http://example.org/orexis/prediction#Flow
description: >-
  What the agent expects a reading to be over a stretch it has not reached - one graph per stretch
  between the instants the reading changes range. The flows moving the property answer rates that
  add, accumulated from the latest percept between happenings; each stretch holds a predicted
  observation of a node of its own, and the planner lays a ground per stretch, where the predicted
  observation's transitions make the subject's foreseen state.
---

# What prediction is for

Prediction is the agent's foresight for the models it holds, and nothing more: it integrates the
flows for what nobody can be asked about, the bed drying from its own latest reading, and what it
writes is a [forecast](/domain/kernel/forecast.md) whose author is this agent. What another holds
the model of — rain, where a peer's van will be — is a forecast too, asked for; the two are one kind
told apart by who said them, and each is laid into the ground of its period as it stands
([foresight-is-derived-where-the-model-is-the-agents-and-asked-for-where-it-is-anothers](/decisions/foresight-is-derived-where-the-model-is-the-agents-and-asked-for-where-it-is-anothers.md),
#992).

# What a flow is

A **flow**, `prediction:Flow`, is one thing that moves a value while nobody acts: a bed drying,
rain wetting it, a barrel leaking, the dose the agent is committed to. The word is system dynamics':
the value is a stock, each flow into or out of it has a rate and a direction, flows sum, and `until`
is the level a flow stops at. It was a drift until #998 - a word for slow, undirected change that fit
the drying and neither the rain nor the dose, which the pages had already taken to calling a flow,
one concept under two words. It says which property it `prediction:moves` and carries
`prediction:rate`, a select answering `?rate` - how fast, per second of the one timeline - for the
subject `$feature` whose value is `$value` at the instant `$at`. It may answer `?low` and `?high`
instead, a rate known only as a range, and `?until`, the value past which it contributes nothing.
A flow reads whatever holds at `$at`: the world's facts, such as `climate:driesPerDay`, a
[forecast](/domain/kernel/forecast.md) hour, a [committed step](/domain/execution/committed-step.md)
inside its landing window - the dose the agent is about to give - another sensor's percept holding then,
and the prediction this agent wrote for another key, the soil's drying reading the air's humidity as the
agent itself foresees it (#996). Every flow moving one property ADDS: the value moves by
the sum, and no flow knows another exists.

# What is written

Started, the package answers every percept and every belief a job writes by one walk over the keys
in the order their flows read each other - `order` reads every `sosa:observedProperty` a rate text names,
and a property is predicted after each it reads, so the prediction a flow reads is written when it is
asked; two properties each moving by the other are a cycle, refused at onboarding and never iterated
to a fixpoint (#996). A percept rewrites that sensor's key and every key whose flows read it; a belief - a
committed step written or closed - rewrites every key's, since what a flow reads has changed; each key
once an arrival, and what the package wrote itself it answers nothing of
([a-package-starts-itself](/decisions/a-package-starts-itself.md)). `predict`
(`agent/prediction/predict.py`) takes the observation a sensor last made - the latest
[percept](/domain/sensing/observation.md), the one begun last, found by sensing's kind, `sensing:ObservationGraph`,
and `sosa:madeBySensor` - the one word of sensing's prediction speaks, from above it, importing none
of its code; prediction is one of the readers at the boundary a percept is handed to - and accumulates the
flows' sum from it as far as the agent looks - `prediction:horizonS`, a
[stance](/domain/kernel/stance.md), a day where it states none. Time is split at every **happening**,
the start or end of a belief graph, a prediction or a percept holding inside that horizon, since only
there can what a flow reads change; between
two, the rates are asked once and held, at most for an hour. Within a segment the value is a
straight line, so a crossing of a bound of every [region](/domain/sensing/region.md) that applies to
what the sensor observes is placed exactly, by division.

What is written is one `orexis:ForecastGraph` per stretch - from the observation's horizon to the
first crossing, crossing to crossing, the last to the horizon's end - holding a predicted
`sosa:Observation` with the number at the last instant of the stretch known to lie on its side -
its key, its sensor, the number and the instant, as ONE node per key and never the percept it was
made from, which crosses into no ground (#944). A stretch supersedes the one before it by key: the
planner laying a ground takes out every triple under a subject and predicate the prediction adds to,
and the prediction says nothing about how (#988). Where a
rate is a range the value is a [corridor](/domain/prediction/corridor.md), and each stretch is its
worst side. A key no flow moves is predicted nothing: a package that declares no flow has
claimed nothing, and the state concluded of the reading is what every ground ahead inherits (#989).

# What is made of it

- **A ground per stretch**, by the [planner](/domain/planning/planner.md)'s `lay_ground`: the present,
  and the present with each prediction applied at its instant - a prediction is a diff, and only a
  ground has applied it - as a forecast received is applied where its period begins (#987). The
  derivation judges every desire in every ground, so a crossing foreseen at noon mints a want at noon.
- **The subject's state in that ground.** The predicted observation arrives in the ground it is laid
  into and triggers the [transitions](/domain/belief/transition.md) there, beside the state the ground
  before held, so the margin holds what is foreseen as it holds the present. The prediction itself
  holds the number and no state (#944).
- **Nothing of the present.** A prediction is derived from a percept as the percept's revision is,
  and is neither; the executor answers a step over the state and its revisions, never over what was
  foreseen.

The next reading is the observation in hand, and every prediction derived from a percept of its sensor
goes before its own are written.

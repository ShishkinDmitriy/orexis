---
type: Domain Concept
title: Prediction
term: http://example.org/orexis/prediction#Drift
description: >-
  What the agent expects a reading to be over a stretch it has not reached - one graph per stretch
  between the instants the reading changes range. The drifts moving the property answer rates that
  add, accumulated from the latest percept between happenings; each stretch holds a predicted
  observation of a node of its own, and the planner lays a ground per stretch, where the predicted
  observation's transitions make the subject's foreseen state.
---

# What a drift is

A **drift**, `prediction:Drift`, is one thing that moves a value while nobody acts: a bed drying,
rain wetting it, a barrel leaking. It says which property it `prediction:moves` and carries
`prediction:rate`, a select answering `?rate` - how fast, per second of the one timeline - for the
subject `$feature` whose value is `$value` at the instant `$at`. It may answer `?low` and `?high`
instead, a rate known only as a range, and `?until`, the value past which it contributes nothing.
A drift reads whatever holds at `$at`: the world's facts, such as `climate:driesPerDay`, a
[forecast](/domain/sensing/forecast.md) hour, and a [committed step](/domain/execution/committed-step.md)
inside its landing window - the dose the agent is about to give. Every drift moving one property ADDS: the value moves by
the sum, and no drift knows another exists.

# What is written

Started, the package answers every percept and every belief a job writes: a percept by rewriting
that sensor's predictions, a belief - a committed step written or closed - by rewriting every key's,
since what a drift reads has changed ([a-package-starts-itself](/decisions/a-package-starts-itself.md)). `predict`
(`agent/prediction/predict.py`) takes the observation a sensor last made - the latest
[percept](/domain/sensing/observation.md), the one begun last, found by sensing's kind, `sensing:ObservationGraph`,
and `sosa:madeBySensor` - the one word of sensing's prediction speaks, from above it, importing none
of its code; prediction is one of the readers at the boundary a percept is handed to - and accumulates the
drifts' sum from it as far as the agent looks - `prediction:horizonS`, a
[stance](/domain/kernel/stance.md), a day where it states none. Time is split at every **happening**,
the start or end of a public or belief graph holding inside that horizon, since only there can what a
drift reads change; between
two, the rates are asked once and held, at most for an hour. Within a segment the value is a
straight line, so a crossing of a bound of every [region](/domain/sensing/region.md) that applies to
what the sensor observes is placed exactly, by division.

What is written is one `orexis:PredictionGraph` per stretch - from the observation's horizon to the
first crossing, crossing to crossing, the last to the horizon's end - holding a predicted
`sosa:Observation` with the number at the last instant of the stretch known to lie on its side -
its key, its sensor, the number and the instant, as a node of its own and never the percept it was
made from, which crosses into no ground (#944) - and carrying on its catalogue row
`orexis:retracts`, the text that takes out of a ground the predicted reading it replaces. Where a
rate is a range the value is a [corridor](/domain/prediction/corridor.md), and each stretch is its
worst side. A key no drift moves is carried forward an hour past the observation, and no further: a
package that declares no drift has claimed nothing past that.

# What is made of it

- **A ground per stretch**, by the [planner](/domain/planning/planner.md)'s `lay_ground`: the present,
  and the present with each prediction applied at its instant - a prediction is a diff, and only a
  ground has applied it. The derivation judges every desire in every ground, so a crossing
  foreseen at noon mints a want at noon.
- **The subject's state in that ground.** The predicted observation arrives in the ground it is laid
  into and triggers the [transitions](/domain/belief/transition.md) there, beside the state the ground
  before held, so the margin holds what is foreseen as it holds the present. The prediction itself
  holds the number and no state (#944).
- **Nothing of the present.** A prediction is derived from a percept as the percept's revision is,
  and is neither; the executor answers a step over the state and its revisions, never over what was
  foreseen.

The next reading is the observation in hand, and every prediction derived from a percept of its sensor
goes before its own are written.

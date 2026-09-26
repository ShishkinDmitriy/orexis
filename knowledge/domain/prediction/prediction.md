---
type: Domain Concept
title: Prediction
term: http://example.org/orexis/prediction#Drift
description: >-
  What the agent expects a reading to be over a stretch it has not reached - one graph per stretch
  between the instants the reading changes range, each holding a predicted observation with the
  number a drift gives there and holding during its window. Its side is concluded by the same
  rules as a real reading's; the planner lays a ground per stretch and searches from each.
---

# What is written

`predict` (`agent/prediction/predict.py`) takes the observation a sensor last made — found by the
kernel's kind and `sosa:madeBySensor`, so nothing of sensing is imported — and runs the domain's
**drifts** over it. A drift, `prediction:Drift`, is what a value does by itself while nobody acts:
a pot drying, a barrel draining. It carries a `sh:construct` answering the predicted observation
`$elapsed` seconds past the one in hand.

The drift is run at the rungs of a ladder — an hour, five and a day past the instant the reading
falls due — and against every [region](/domain/sensing/region.md) that applies to what the sensor
observes, each crossing of a bound between two rungs is bisected. What is written is one
`orexis:PredictionGraph` per stretch: from the horizon to the first crossing, crossing to
crossing, and from the last to the ladder's end. Each holds a predicted `sosa:Observation` with
the number the drift gives at the last instant of the stretch known to lie on its side, and each
carries on its catalogue row `orexis:retracts`, the text that takes out of a ground the reading
it replaces. A key no drift moves is carried forward for the first rung alone.

The ladder is the scan, not the answer: what is written is where the side changes.

# What is made of it

- **Its side**, by [revision](/domain/belief/revision.md): sensing's rules conclude `below`, `inside`
  or `above` of a predicted observation exactly as of a real one, so a stretch reads as the side it
  is and no width is ever added to a number.
- **A ground per stretch**, by the [planner](/domain/planning/planner.md)'s `lay_ground`: the present,
  and the present with each prediction applied at its instant — a prediction is a diff, and only a
  ground has applied it. The derivation judges every desire in every ground, so a crossing
  foreseen at noon mints a want at noon.
- **Nothing of the present.** A prediction and a revision are derived from the same observation,
  and only the revision is a belief; the executor answers a step over the readings and their
  revisions, never over what was foreseen.

The next reading replaces the observation, and every prediction derived from it goes with it.

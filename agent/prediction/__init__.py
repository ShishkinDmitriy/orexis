"""The prediction package of Agent 0.2.0: when a reading changes range, and nothing else.

**A PREDICTION IS THE CALCULATION OF WHEN THE READING CHANGES RANGE.** `predict` takes the
observation a sensor last made — found by the kernel's kind, `orexis:StateGraph`, and SOSA's
`sosa:madeBySensor`, so nothing of the sensing layer is imported or spoken — runs the
domain's drifts over it at the rungs of a ladder that is this package's scan, bisects every
crossing of a bound of the ranges that apply to what the sensor observes (SSN-System's,
`ranges_of`), and writes one `orexis:PredictionGraph` per stretch between crossings, holding a
predicted `sosa:Observation` with the number the drift gives on that side. Which side a
stretch is on is not said here: it is a revision the sensing layer's rules conclude of the
predicted observation as of the real one, run by the deliberator when the container says
the graph changed.

**ONE WORD OF ITS OWN**, `prediction:Drift`: what a value does by itself while nobody acts,
which no `sosa:Procedure` is. A drift carries `sh:construct` and declares no horizon.

It was sensing's `predict` until the sovereign split it out (2026-09-24), so that sensing
observes and says when a sensor has gone silent, and predicts nothing.
"""

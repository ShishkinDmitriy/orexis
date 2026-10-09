"""The prediction package of Agent 0.2.0: when a reading changes range, and nothing else.

**A PREDICTION IS THE CALCULATION OF WHEN THE READING CHANGES RANGE.** `predict` takes the
observation a sensor last made — found by the kernel's kind, `orexis:StateGraph`, and SOSA's
`sosa:madeBySensor`, so nothing of the sensing layer is imported or spoken — sums the rates of
every drift moving what it observes, accumulates the sum between the happenings at which what a
drift reads may change, places every crossing of a bound of the ranges that apply to what the
sensor observes (SSN-System's, `ranges_of`) exactly — leaving a side where a range's margin
(`orexis:margin`) says, walked from the side the observation is on — and writes one
`orexis:PredictionGraph` per stretch between crossings, holding a predicted `sosa:Observation`
with its number and, where a range states a margin, its stretch's side carried. A rate known as a
range gives a corridor, and a stretch is its worst side. Which side a stretch is on is not said
here: it is a revision the sensing layer's rules conclude of the predicted observation as of the
real one.

**ITS OWN WORDS**, `prediction:Drift` — one thing that moves a value while nobody acts, which no
`sosa:Procedure` is — the property it `prediction:moves` and its `prediction:rate`, a select
answering how fast. Drifts moving one property add.

It was sensing's `predict` until the sovereign split it out (2026-09-24), so that sensing
observes and says when a sensor has gone silent, and predicts nothing.
"""

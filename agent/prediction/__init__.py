"""The prediction package of Agent 0.2.0: when a reading changes range, and nothing else.

**A PREDICTION IS THE CALCULATION OF WHEN THE READING CHANGES RANGE.** `foresee` hands the
planner the flows' integration, which it advances as it lays the grounds: from each ground, every
key of the agent together, the rates of every flow moving a key's property summed and accumulated
between the happenings at which what a flow reads may change, and every crossing of a bound of the
ranges that apply to what a sensor observes (SSN-System's, `ranges_of`) placed exactly — the place
the next ground is laid, with a predicted `sosa:Observation` arriving there. No forecast graph is
written: the predictor's foresight is the grounds (a-flow-is-integrated-where-the-ground-is-laid,
#1000). A rate known as a range gives a corridor, and a stretch is its worst side. Which side a
stretch is on is not said here: it is what the domain's transitions conclude of the predicted
observation in the ground it arrives in.

**ITS OWN WORDS**, `prediction:Flow` — one thing that moves a value while nobody acts, which no
`sosa:Procedure` is — the property it `prediction:moves` and its `prediction:rate`, a select
answering how fast. Flows moving one property add.

It was sensing's `predict` until the sovereign split it out (2026-09-24), so that sensing
observes and says when a sensor has gone silent, and predicts nothing.
"""

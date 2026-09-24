---
type: Domain Concept
title: Prediction
term: http://example.org/orexis#PredictionGraph
description: >-
  What an agent expects the world to hold at a horizon it has not reached. In 0.1.0 a set of
  bands, wider the further out, never a value. In Agent 0.2.0 a predicted observation with its
  NUMBER, one per stretch between the instants the reading changes range, which is what the
  prediction package's `predict` calculates; which side of a range it is on is a revision
  sensing's rules conclude of it. A prediction of a fluent is a graph holding during a period; the next
  reading rewrites the ladder.
---

# What it is

A **prediction** is what an agent expects to hold at an instant it has not reached, and it
is stated the way this project states not knowing: as a [band](/domain/band.md), or a set of
them. A value is not a different kind of prediction; it is a band collapsed to a point, and a
reading that carries one is the degenerate case of a set with one member. The core never
compares the number, only the bands
([deliberation-is-on-triples-and-a-number-is-not-special](/decisions/deliberation-is-on-triples-and-a-number-is-not-special.md)).

**The further the horizon, the wider the set.** Now the pot reads in its region; in an hour it
is still there; in five it may be in the region or below it; in a day it may be anywhere. Each
step out adds what the instrument cannot see and what the rate cannot promise, so the set of
bands a reading may be in grows until it is every band, which is the honest way of saying the
agent knows nothing that far ahead. The record is
[a-prediction-is-a-set-of-bands-that-widens-with-the-horizon](/decisions/a-prediction-is-a-set-of-bands-that-widens-with-the-horizon.md).

# Two kinds, placed two ways

A **fluent** holds during a stretch, and a prediction of one is a graph holding during a
period — a forecast of the outside, read by the door at the instant a rule asks about
([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)).

An **event** is not stretched: it occurs at an instant, and before it occurs what is known is
the window it is expected in. A prediction of one is an **expected occurrence**, a fact ABOUT
that window stated inside a graph whose own period says how long it is worth
believing. An observation is an event, `sosa:resultTime` its instant once it has occurred;
the **first prediction** is the prediction of it, the one the next reading is held to: the window the instrument's
cadence gives, and the bands the [drift](/domain/effect.md) applied over that window gives.
Sensing writes it after every reading, as the first of the PREDICTIONS the drifts give (#642):
a graph holding during the window, `orexis:PredictionGraph`, carrying the predicted reading
keyed as the present's reading is and typed with every band it may be in — the drift's centre
at the window's far end, widened inside the domain's own rule by the instrument's `sensing:noise`
and the spread the world states beside the rate, so no number leaves the rule. The window is
due when the cadence in force makes the next reading so and closed when the grace runs out; the
package's own horizons follow (`sensing:atHorizon`), one prediction each. A world stating no
width gets the band the drift reaches alone. The next reading rewrites the ladder; the first
window closing with none takes it away and marks the reading stale, which is staleness said
once. A prediction is a reading in a predicted world and IS each band it may be in there — a
shape refusing one refuses the world, the safe direction. A reader asking at an instant is handed
the prediction holding then; the agent's records never list it; and the search reads it at a node's instant
in place of the reading the world holds, except a key the plan itself changed, a key being
changed when its canonical facts are — a look changes none (#643). The
crossing a root foresees is the start of the earliest prediction at which the root reads unmet.

# An intention changes it

The ladder is the world's own branch, what happens if nothing is done. An adopted plan is
the agent choosing another branch, so it changes the prediction (#639): when the
[keeper](/domain/keeper.md) opens an expectation on a step it tells sensing the band the step
declared and the instant it lands, and from that instant on the predictions of the key are
the step's band, the drift's own before it and again once the expectation closes. One ladder, the
do-nothing branch until an [intention](/domain/intention.md) stands and the intended branch
after, and a surprise is a reading outside whichever the agent is on. A reading is compared
with the prediction once at arrival, and that comparison is the step's verdict.

# What it is for

- A reading that lands inside its expected set is the world going on as believed, and does
  not wake the mind; one outside it is a surprise, caught at arrival and named on the pass.
  That is the [reviser](/domain/reviser.md)'s filter (#632).
- A reading that does not land in its window is a missed expected event, which is what
  staleness always was, said once.
- The crossing a root foresees is the first horizon at which the set no longer holds the
  region band — the safe direction, since not knowing is maximal.

# Related

- [the-drift-is-sensings-and-its-result-is-predictions](/decisions/the-drift-is-sensings-and-its-result-is-predictions.md)
  — the grooming: sensing runs every drift and writes predictions, one graph per horizon
  holding during its window, the predicted reading typed with every band it may be in; the
  core reads them at a node's instant and runs no rule, and the reading's arrival is
  compared with the first once, for the keeper, the reviser and staleness alike. The words
  above are #631's rendering until #642 lands.
- [band](/domain/band.md) — the crisp thing a prediction is made of.
- [interval](/domain/interval.md) — why the width lives in the domain's measure and never in
  the core.
- [effect](/domain/effect.md) — the drift, which gives a prediction its centre.

# In Agent 0.2.0, a prediction is when the reading changes range

The set of bands above is the 0.1.0 tree's. In `agent/prediction/` — a package of its own
above sensing, importing nothing of it, since the sovereign asked that sensing observe and say
when a sensor has gone silent and predict nothing — `predict` takes the observation a sensor
last made, found by the kernel's kind and `sosa:madeBySensor`, runs the domain's drifts over it
at the rungs of the ladder and, against every range that applies to what the sensor observes,
bisects each crossing of a bound; what it writes is one
`orexis:PredictionGraph` per stretch — from the horizon to the first crossing, crossing to
crossing, and from the last to the ladder's end — each holding a predicted `sosa:Observation`
in SOSA's words with the number the drift gives at the last instant of that stretch known to
lie on its side. No band is written: the side of a predicted observation is a
[revision](/domain/revision.md), concluded by the rules sensing registers exactly as for the
observation itself, so the mind reads a stretch as the side it is. The drift is the package's
one word, `prediction:Drift` — what a value does by itself while nobody acts, which no
`sosa:Procedure` is — carrying `sh:construct` and no horizon. The ladder is the scan, not the
answer, and it is the package's own — an hour, five and a day past the instant the reading
falls due; a key no drift moves is carried forward for the first rung alone; a key that
crosses nothing has one prediction to the ladder's end.


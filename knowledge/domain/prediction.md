---
type: Domain Concept
title: Prediction
term: http://example.org/orexis#PredictionGraph
description: >-
  What an agent expects the world to hold at a horizon it has not reached — always a SET of
  bands, never a value, and wider the further out. A value is a band collapsed to a point. A
  prediction of a fluent is a graph holding during a period; a prediction of an event, an
  observation, is an expected occurrence stated inside a graph, carrying the window it is
  expected in and the bands it may carry. The first element of the sequence is the expected
  next observation, from the instrument's cadence and the drift, which sensing writes after
  every reading; the far end is every band, which is not knowing said honestly.
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
that window stated inside a graph whose own period says how long the expectation is worth
believing. An observation is an event, `sosa:resultTime` its instant once it has occurred;
the **expected next observation** is the prediction of it: the window the instrument's
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
shape refusing one refuses the world, the safe direction. The door hands the prediction holding
at an instant; the agent's records never list it; and the search reads it at a node's instant
in place of the reading the world holds, except a key the plan itself changed, a key being
changed when its canonical facts are — a look changes none (#643). The
crossing a root foresees is the start of the earliest prediction at which the root reads unmet.

# An intention changes it

The ladder is the world's own branch, what happens if nothing is done. An adopted plan is
the agent choosing another branch, so it changes the prediction (#639): when the
[keeper](/domain/keeper.md) opens a watch on a step it tells sensing the band the step
declared and the instant it lands, and from that instant on the predictions of the key are
the step's band, the drift's own before it and again once the watch closes. One ladder, the
do-nothing branch until an [intention](/domain/intention.md) stands and the intended branch
after, and a surprise is a reading outside whichever the agent is on. A reading is compared
with the prediction once at arrival, and that comparison is the step's verdict.

# What it is for

- A reading that lands inside its expected set is the world going on as believed, and is not
  worth waking the mind for; one outside it is a surprise, caught at arrival. That is the
  filter the [reviser](/domain/reviser.md) has been waiting for.
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

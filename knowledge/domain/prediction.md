---
type: Domain Concept
title: Prediction
term: http://example.org/orexis/sensing#ExpectedObservation
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
Sensing writes it after every reading (#631), into a working graph of the agent's own — never
carried into a plan's imaginarium, since the search plans on readings — one node per
subject and property keyed as the reading is: `sensing:ExpectedObservation`, its window as
`dcterms:temporal` on the node — due when the cadence in force makes it so, closed when the
grace runs out — its subject and property in sensing's own words (`sensing:expectedOf`,
`sensing:expectedProperty`), never the observation's, so nothing walking a subject's
observations reaches it — and the bands it `sensing:mayBe`, the drift's centre at the window's far
end widened by the instrument's `sensing:noise` and by what the drift states beside its rate
(`orexis:spreadsBy`). A world stating no width gets the band the drift reaches alone. The
next reading replaces it; a window that closes with none takes it away, which is staleness
said once. It is not an observation, and no rule reading readings reads it as one.
The host's debt, carrying the window its holder may come in, is the same shape for an
arrival ([obligation](/domain/obligation.md)).

# An intention changes it

The sequence of expected observations is a discrete rendering of the formula the drift is —
the reading over time, with the width the domain states growing along it — and it is the
world's own branch, what happens if nothing is done. An adopted plan is the agent choosing
another branch, so it changes the prediction: past each step's landing the expected bands are
the step's predicted effect, which the [keeper](/domain/keeper.md) already holds the world to
as the step's expectation, and the drift runs on from there. One sequence, the do-nothing
branch until an [intention](/domain/intention.md) stands and the intended branch after, and a
surprise is a reading outside whichever the agent is on.

# What it is for

- A reading that lands inside its expected set is the world going on as believed, and is not
  worth waking the mind for; one outside it is a surprise, caught at arrival. That is the
  filter the [reviser](/domain/reviser.md) has been waiting for.
- A reading that does not land in its window is a missed expected event, which is what
  staleness always was, said once.
- The crossing a root foresees is the first horizon at which the set no longer holds the
  region band — the safe direction, since not knowing is maximal.

# Related

- [band](/domain/band.md) — the crisp thing a prediction is made of.
- [interval](/domain/interval.md) — why the width lives in the domain's measure and never in
  the core.
- [effect](/domain/effect.md) — the drift, which gives a prediction its centre.

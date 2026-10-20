---
type: Domain Concept
title: Prediction
term: http://example.org/orexis/prediction#Flow
description: >-
  What the agent expects a reading to be over a stretch it has not reached - the flows moving the
  property answer rates that add, integrated from each ground as the planner lays them, every key
  of the agent advancing together. A crossing of a range bound is where the next ground is laid,
  and the predicted observation arrives there for the transitions to judge; no forecast of the
  predictor's own is written.
---

# What prediction is for

Prediction is the agent's foresight for the models it holds, and nothing more: it integrates the
flows for what nobody can be asked about, the bed drying from its own latest reading, and what it
answers is where the next ground is laid and what arrives there. What another holds the model of -
rain, where a peer's van will be - is a [forecast](/domain/kernel/forecast.md), asked for and
believed; the flows read it beside the ground at the instant they are asked at
([foresight-is-derived-where-the-model-is-the-agents-and-asked-for-where-it-is-anothers](/decisions/foresight-is-derived-where-the-model-is-the-agents-and-asked-for-where-it-is-anothers.md)).

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
A flow reads whatever holds at `$at`: the ground the planner stands in - the states the transitions
made, a peer's position laid where its forecast begins - and beside it every graph holding at that instant
by the period its row states, such as `climate:driesPerDay` on the bed, a
[forecast](/domain/kernel/forecast.md) hour of rain, a [committed step](/domain/execution/committed-step.md)
inside its landing window; and the numbers every key stands at, so the soil's drying reads the air's
humidity as the agent itself foresees it at that instant. Its own key's number is `$value`, the one
number a flow is owed. Every flow moving one property ADDS: the value moves by the sum, and no flow
knows another exists.

# How it is integrated

The flows are integrated **from each ground, as the grounds are laid**
([a-flow-is-integrated-where-the-ground-is-laid](/decisions/a-flow-is-integrated-where-the-ground-is-laid.md),
#1000). At link the planner's part takes the package's `foresee`, and at the start of a pass the
[planner](/domain/planning/planner.md) makes the foresight from the belief base: each sensor's latest
[percept](/domain/sensing/observation.md) - found by sensing's kind, `sensing:ObservationGraph`, and
`sosa:madeBySensor`, the one word of sensing's prediction speaks, from above it, importing none of its
code - with what the rules concluded of it, its key and its number; the flows moving its property, off
the flow graphs alone; the ranges that apply to it; and how far the agent looks, `prediction:horizonS`,
a [stance](/domain/kernel/stance.md), a day where it states none. A key no flow moves is foreseen
nothing: a package that declares no flow has claimed nothing, and the state concluded of the reading
is what every ground ahead inherits (#989).

Then, ground by ground, `lay_ground` **advances** it to the next boundary it knows of - a belief
ahead beginning, a step landing - and the integration runs in that ground: every key's flows are asked
at the same instants over the same graphs and the same numbers, and every key moves by its own sum.
Soil reading air and air reading soil are two coupled flows, not a cycle, and nothing orders the keys.
Between two grounds the rates are asked again at every **happening**, the start or end of a belief
holding inside the stretch, since only there can what a flow reads change, and at most an hour apart.
Within a segment the value is a straight line, so a crossing of a bound of every
[region](/domain/sensing/region.md) that applies to what the sensor observes is placed exactly, by
division. Where a rate is a range the value is a [corridor](/domain/prediction/corridor.md).

# What is answered

The next **knot**: the earliest instant at which a key of the scope crosses a bound, with a predicted
`sosa:Observation` for each key crossing there - its feature, property and sensor, the number and the
instant, ONE node per key, never the percept it was made from, which crosses into no ground (#944).
The number is read at the far end of the stretch the crossing opens, the next crossing or the hour's
end, the last instant known to lie on the new side, so the side as written is the stretch's and not
the bound's edge. Where no key crosses, the hour's end is the knot for every key that moved, with the
number it then stands at, since a state the transitions hold past its bound by a margin prediction does
not read is judged again within the hour. The planner lays a ground at the knot, the observation
arrives in it and triggers the [transitions](/domain/belief/transition.md) there, beside the state the
ground before held, so the margin holds what is foreseen as it holds the present; the ground keeps the
state they made and no number, and one that changes no state collapses into the one before it.

**Nothing is written into the belief base.** The numbers live in a working graph of the package's own
beside the grounds while they are laid and go when the laying is done; no `orexis:ForecastGraph` of the
predictor's is a graph anyone holds, hashes, cuts or forgets, and the present is never written to. What
outlives the pass is the grounds in the [imaginarium](/domain/planning/imaginarium.md), which the
derivation judges every desire in - so a crossing foreseen at noon mints a want at noon - and which
the next pass lays again from the readings then in hand.

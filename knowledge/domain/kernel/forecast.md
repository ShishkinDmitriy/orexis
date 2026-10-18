---
type: Domain Concept
title: Forecast
term: http://example.org/orexis#ForecastGraph
description: >-
  Anyone's word about what will hold over a stretch ahead - rain for the hour after next, where a
  peer's van will be, the dose the agent is committed to - as a graph holding during the stretch it
  is about. One kind, `orexis:ForecastGraph`, a belief; who said it is provenance, and each author
  replaces its own. The agent's own foresight of its readings is none: it is the grounds.
---

# What it is

A forecast is a word about what will hold over a stretch the present has not reached, kept as a
graph that holds during that stretch and carries what is said to hold then: a weather service's
`sosa:Observation` of rain for one hour, a peer's `courier:at` for a cell, the step the executor is
committed to over its landing window. A reader standing at an instant inside the stretch reads it and
one standing before it does not
([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)), and where a text of
the pass or a transition reads what it says, the [planner](/domain/planning/planner.md) lays it into
the ground of its period where that period begins, superseding by key, as #987 lays every belief the
present has not reached.

**One kind, whoever said it.** The planner needs one thing of a forecast, that it holds later, and that
is a fact about the timeline and not about a class of beings
([foresight-is-derived-where-the-model-is-the-agents-and-asked-for-where-it-is-anothers](/decisions/foresight-is-derived-where-the-model-is-the-agents-and-asked-for-where-it-is-anothers.md),
#992). So a [committed step](/domain/execution/committed-step.md) is a forecast of the agent's own act
and a received hour a forecast of a service's: what differs is provenance, `orexis:arrivedBy` and
`prov:wasDerivedFrom`, and what depends on the author is who replaces it, which each author finds by
its own provenance - sensing by the sensor that read the series, the executor by the step.

**The agent's own foresight of its readings is no forecast.** What the predictor foresees of a probe
is the integration of the [flows](/domain/prediction/prediction.md), run from each ground as the
planner lays them, and what it comes to is the grounds themselves - the state a crossing makes, judged
by the transitions where it is laid - and no graph of the belief base
([a-flow-is-integrated-where-the-ground-is-laid](/decisions/a-flow-is-integrated-where-the-ground-is-laid.md),
#1000). The predictor's stretches were forecasts of this kind from #992 to #1000, told from the
received by being recorded; nothing is told apart now, since nothing of the predictor's is written.

It is a belief, not a reading: no forecast is a `sensing:ObservationGraph`, so the predictor never
takes one for the observation in hand. A flow reads a forecast of any author at the instant it is asked
at, by the period its row states, beside the ground - a committed step inside its window, a rain hour
while it falls - and the start or end of its stretch is a happening of the integration, where the rates
are asked again.

# Where it comes from

- **A sensor that reads a SERIES**: one stating `sensing:endsPointer` or `sensing:startsPointer` beside
  its `sensing:readingPointer`, so that one response carries many values and the instants they are
  for. [Sensing](/domain/sensing/sensing.md)'s `received` writes one forecast per stretch still ahead
  and forgets the sensor's earlier ones; how the response arrives is the
  [transport](/domain/transport/transport.md)'s, over HTTP from a Thing Description
  ([a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md)).
- **The executor**, one per step an intention adopted, over its landing window
  ([committed step](/domain/execution/committed-step.md)).
- **A peer**, heard through speech and extracted
  ([extraction](/domain/speech/extraction.md)).

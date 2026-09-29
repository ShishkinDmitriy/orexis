---
type: Domain Concept
title: Forecast
term: http://example.org/orexis/sensing#ForecastGraph
description: >-
  Another party's word about a stretch ahead - rain for the hour after next - as a graph holding
  during the stretch it is about. What a sensor reading a series writes, one graph per stretch,
  replaced by the next forecast. Testimony, never the agent's own prediction.
---

# What it is

A forecast is what someone other than the agent says a quantity will be over a stretch it has not
reached: a weather service's rain for one hour. It is a graph, `sensing:ForecastGraph`, holding
during the stretch it is about and carrying one `sosa:Observation` of the property, of the place,
with the number it gives - so a reader standing at an instant inside that stretch reads it and one
standing before it does not
([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)). It is a belief,
not a reading: it is not an `orexis:StateGraph`, so no plan forks it and the prediction package
never takes it for the observation in hand.

It is not a [prediction](/domain/prediction/prediction.md). A prediction is the agent's own
calculation, derived from its last observation and replaced with it; a forecast is testimony,
kept because it arrived and replaced when the next one does. A drift reads a forecast, and the
start and end of its stretch are happenings of the calculation.

# Where it comes from

A sensor that reads a SERIES: one stating `sensing:endsPointer` or `sensing:startsPointer`
beside its `sensing:readingPointer`, so that one response carries many values and the instants
they are for. [Sensing](/domain/sensing/sensing.md)'s `received` writes one forecast per stretch
still ahead and forgets the sensor's earlier ones; `missed` says the sensor is due when none
stands or the standing one was issued a cadence ago. How the response arrives is the
[transport](/domain/transport/transport.md)'s - over HTTP, from a Thing Description
([a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md)).

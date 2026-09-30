---
type: Domain Concept
title: Observation
term: http://www.w3.org/ns/sosa/Observation
description: >-
  One act of observing, as SOSA says it - which sensor, the number it gave, when - and, concluded by
  sensing's rules, which property of which feature and the quantity. One per sensor, in a graph of
  its own that the next reading replaces whole; the premise every side and every prediction is
  derived from.
---

# What it is

```turtle
# the sensor's graph, as `received` writes it: what the sensor gave
:obs_probe a sosa:Observation ; sosa:madeBySensor :probe ; sensing:rawResult 2412 ;
    sosa:resultTime "2026-09-20T12:00:00Z"^^xsd:dateTime .
# its revision, as sensing's rules conclude it from the topology and the calibration
:obs_probe sosa:observedProperty climate:SoilMoisture ; sosa:hasFeatureOfInterest :fern ;
    sosa:hasSimpleResult 0.414737 .
```

Written by [sensing](/domain/sensing/sensing.md)'s `received` into an `sensing:ObservationGraph`
named for its sensor. A sensor holds ONE observation: a new reading does not join the old one, it
replaces the graph, so a reader asking what the soil is finds one number, and the graph's period
says how long that number is worth believing — until the next is due. What it is OF and its
[reading](/domain/sensing/reading.md) are in its revision, so a reader of an observation reads the graph
and its revisions together (`store.revisions_of`), as the planner's ground and the prediction do.

# Why it is kept

It is testimony, the one thing in the store that is somebody else's word (`orexis:Received`), and
it is the premise: what a rule concludes of it is a [revision](/domain/belief/revision.md) in a
graph derived from it, and what a drift makes of it is a
[prediction](/domain/prediction/prediction.md). Both go when it is replaced, because both were
about it. The number it carries is the [reading](/domain/sensing/reading.md).

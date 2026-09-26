---
type: Domain Concept
title: Observation
term: http://www.w3.org/ns/sosa/Observation
description: >-
  One act of observing, as SOSA says it - which sensor, which property of which feature, the
  number, when. One per key, the sensor's property and what it is hosted by, in a graph of its
  own that the next reading replaces whole; the premise every side and every prediction is
  derived from.
---

# What it is

```turtle
[] a sosa:Observation ;
    sosa:madeBySensor :probe ; sosa:observedProperty climate:SoilMoisture ;
    sosa:hasFeatureOfInterest :fern ; sosa:hasSimpleResult 0.27 ;
    sosa:resultTime "2026-09-20T12:00:00Z"^^xsd:dateTime .
```

Written by [sensing](/domain/sensing/sensing.md)'s `received` into an `sensing:ObservationGraph`
named for its key. A key holds ONE observation: a new reading does not join the old one, it
replaces the graph, so a reader asking what the soil is finds one number, and the graph's period
says how long that number is worth believing — until the next is due.

# Why it is kept

It is testimony, the one thing in the store that is somebody else's word (`orexis:Received`), and
it is the premise: what a rule concludes of it is a [revision](/domain/belief/revision.md) in a
graph derived from it, and what a drift makes of it is a
[prediction](/domain/prediction/prediction.md). Both go when it is replaced, because both were
about it. The number it carries is the [reading](/domain/sensing/reading.md).

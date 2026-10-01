---
type: Domain Concept
title: Calibration
term: http://example.org/orexis/sensing#TwoPointCalibration
description: >-
  A correction within one unit - how a quantity an instrument reports with an error is the true one,
  a thermometer reading 0.4 in ice water - stated by the world beside the sensor as two points, and
  applied by sensing's rule after any scaling. A sensor no calibration corrects keeps its scaled quantity.
---

# What the world states

```turtle
:thermo_calibration a sensing:TwoPointCalibration ;
    sensing:corrects :air_temp_terrace ;
    sensing:point [ rdfs:label "ice" ; sensing:reads 0.4 ; sensing:standsFor 0.0 ] ,
                  [ rdfs:label "boiling" ; sensing:reads 99.1 ; sensing:standsFor 100.0 ] .
```

Two points, each what the sensor reads there in its own unit and what is true. Sensing's rule applies it
at layer 1, over the [scaling](/domain/sensing/scaling.md)'s quantity — the number as it is where no
scaling scales the sensor — and what comes out is the observation's
[reading](/domain/sensing/reading.md), on the straight line through the points, unclamped. Where a
scaling changes the unit, a calibration keeps it: the two are told apart so that one probe may be
rescaled and its rescaled quantity corrected, each measured on its own. No world states one yet.

Finding the points is a person's work for now — the instrument at a reference, its reading taken, the
number written into the world — and #862 would make it a plan the agent walks with that person.

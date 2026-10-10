---
type: Domain Concept
title: Scaling
term: http://example.org/orexis/sensing#TwoPointScaling
description: >-
  A rescale - how a sensor's number becomes a quantity in another unit, a probe's ADC count a
  fraction of saturation - stated by the world beside the sensor as two points, and applied by
  sensing's rule as the deliberator revises the reading. A sensor no scaling scales gives its number
  as its quantity.
---

# What the world states

```turtle
:probe_scaling a sensing:TwoPointScaling ;
    sensing:scales :moisture_sensor_terrace ;
    sensing:point [ rdfs:label "dry" ; sensing:reads 3200 ; sensing:standsFor 0.0 ] ,
                  [ rdfs:label "wet" ; sensing:reads 1300 ; sensing:standsFor 1.0 ] .
```

One object per instrument it rescales, two points apiece: what the sensor reads there and what that
stands for. [Sensing](/domain/sensing/sensing.md)'s rule places the number the sensor gave on the
straight line through them at layer 0, as `sensing:scaledResult`, unclamped — a probe in water past the
wet point reads past one, which a transition then judges against its [region](/domain/sensing/region.md), rather than a saturated
one hiding a flooded or frozen probe. A thermometer already reports degrees and states no scaling.

What a scaling changes is the UNIT; what corrects an instrument's error within its own unit is a
[calibration](/domain/sensing/calibration.md), applied after it.

# Measuring it again

The points are the world's, so a new measurement is two numbers edited and the agent restarted: a
lived-in volume reads every public graph again at boot. The count to put there is in the agent's log,
which says what each sensor gave as it arrives ([calibrate-a-probe](/runbooks/calibrate-a-probe.md)).

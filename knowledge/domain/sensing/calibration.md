---
type: Repository
title: Calibration
term: http://example.org/orexis/sensing#CalibrationGraph
description: >-
  The agent's own belief of how a sensor's number is a quantity - two calibration points, each a
  number the sensor reads and the quantity it stands for, named dry or wet - read by sensing's rule
  to conclude an observation, and revised by telling the agent what the sensor reads now.
---

# What it holds

```turtle
:moisture_sensor_terrace sensing:calibrationPoint
    [ rdfs:label "dry" ; sensing:raw 3200 ; sensing:quantity 0.0 ] ,
    [ rdfs:label "wet" ; sensing:raw 1300 ; sensing:quantity 1.0 ] .
```

A `sensing:CalibrationGraph` of the agent's own, one per agent, born from the agent's document under
the world's `beliefs/`. A sensor with two points has its number placed on the straight line through
them by [sensing](/domain/sensing/sensing.md)'s rule, unclamped: a probe in water past the wet point
reads past one, which a [side](/domain/sensing/region.md) then says, rather than a saturated one hiding
a flooded or frozen probe. A sensor with none gives its quantity as its number, which is what a
thermometer reporting degrees does.

# Why it is the agent's

It is one agent's understanding of one probe in one bed, and it drifts; a board that scaled with it
had to be retrieved to be recalibrated, and a world document stating it would be every reader's
fact about a thing only this agent handles. So it is a belief the agent revises: `calibrate` gives the
point a label names the number the sensor's latest [observation](/domain/sensing/observation.md) holds,
or one the teller says, and a lived-in volume keeps the revision across restarts while the document
stays what a newborn agent believes. `orexis-calibrate <world> <agent> <sensor> dry` does it for a
running agent ([calibrate-a-probe](/runbooks/calibrate-a-probe.md)).

It is public knowledge the agent owns, as a derivation graph is, because what a reading is revised
beside is public knowledge and the rule reads the points there
([an-observation-is-concluded-from-the-number-a-sensor-gave](/decisions/an-observation-is-concluded-from-the-number-a-sensor-gave.md)).

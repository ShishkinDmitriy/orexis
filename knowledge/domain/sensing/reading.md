---
type: Domain Concept
title: Reading
term: http://www.w3.org/ns/sosa/hasSimpleResult
description: >-
  The quantity an observation carries - the value of a property, concluded by sensing's rules from
  the number the sensor gave, through the scaling and calibration the world states. What a plan moves, what a side
  is concluded of and a subject belief judged from, what a drift predicts forward; it ages by its period rather
  than by being overwritten, and it is the one belief a peer or a device can be wrong about.
---

# What it is

`sosa:hasSimpleResult` on an [observation](/domain/sensing/observation.md): 0.27 for the fern's
soil, 18.5 for the greenhouse air — the sensor's number as it is where the number is already a
quantity, a thermometer's degrees, or rescaled through its [scaling](/domain/sensing/scaling.md), a
probe's count made a moisture, and corrected through its [calibration](/domain/sensing/calibration.md)
where the world states one. The agent reads it and never writes it — except where an action
is fictive and the executor, being the world, writes what the step predicted.

# What is made of it

- **A side** — `sensing:below`, `inside` or `above` a [region](/domain/sensing/region.md), concluded
  by sensing's rules as a [revision](/domain/belief/revision.md). A met-test reads the side, not the
  number: the core compares triples and interprets no literal.
- **A subject belief** — the state a domain's [transition](/domain/belief/transition.md) judges its
  subject in against the operating range, beside the [subject belief](/domain/belief/subject-belief.md)
  before it and held by the range's [margin](/domain/sensing/margin.md), in the domain's words and
  with no number: the reading stays here.
- **The stretches ahead** — the [prediction](/domain/prediction/prediction.md) package runs the
  domain's drift over it and writes one predicted reading per stretch between range crossings.
- **A step's size** — a dose is sized from how far the reading is below the middle of its range,
  when the step is taken, by the action's command.

# What it is not

Not a [series](/domain/kernel/series.md) point. Sensing also says each reading as it is concluded,
and history writes it for the panels to draw; that series is watched and never believed. And not the
number the sensor gave (`sensing:rawResult`), which is kept beside it as what the rules conclude it
from.

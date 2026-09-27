---
type: Domain Concept
title: Reading
term: http://www.w3.org/ns/sosa/hasSimpleResult
description: >-
  The number an observation carries - the value of a property as an instrument reported it, after
  the pipeline. What a plan moves, what a side is concluded of, what a drift predicts forward; it
  ages by its period rather than by being overwritten, and it is the one belief a peer or a device
  can be wrong about.
---

# What it is

`sosa:hasSimpleResult` on an [observation](/domain/sensing/observation.md): 0.27 for the fern's
soil, 18.5 for the greenhouse air. The agent reads it and never writes it — except where an action
is fictive and the executor, being the world, writes what the step predicted.

# What is made of it

- **A side** — `sensing:below`, `inside` or `above` a [region](/domain/sensing/region.md), concluded
  by sensing's rules as a [revision](/domain/belief/revision.md). A met-test reads the side, not the
  number: the core compares triples and interprets no literal.
- **The stretches ahead** — the [prediction](/domain/prediction/prediction.md) package runs the
  domain's drift over it and writes one predicted reading per stretch between range crossings.
- **A step's size** — a dose is sized from how far the reading is below the middle of its range,
  when the step is taken, by the action's command.

# What it is not

Not a [series](/domain/kernel/series.md) point. Sensing also contributes each reading to the
agent's history as it writes it, for the panels to draw, and that series is watched and never
believed.
